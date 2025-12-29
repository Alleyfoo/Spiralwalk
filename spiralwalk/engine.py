import json
import logging
import signal
import threading
import time
from pathlib import Path
from typing import Dict, List

from .clock import ClockFollower
from .config import Settings
from .lanes import Lane
from .midi_io import MidiInput, MidiOutput
from .spiral import SpiralWalker

logger = logging.getLogger(__name__)


class AutomationEngine:
    def __init__(
        self,
        settings: Settings,
        dry_run: bool = False,
        freeze_scene: bool = False,
        frozen_lanes: list[str] | None = None,
        session_log_path: str | None = None,
        arm_ticks: int = 0,
        virtual_in: bool = False,
        virtual_out: bool = False,
        in_port_override: str | None = None,
        out_port_override: str | None = None,
        soft_start: bool = False,
    ):
        self.settings = settings
        self.dry_run = dry_run
        self.freeze_scene = freeze_scene
        self.frozen_lanes = set(frozen_lanes or [])
        self.session_log_path = Path(session_log_path) if session_log_path else None
        self.arm_ticks = max(0, arm_ticks)
        self.virtual_in = virtual_in
        self.virtual_out = virtual_out
        self.in_port_override = in_port_override
        self.out_port_override = out_port_override
        self.soft_start = soft_start

        self.clock = ClockFollower(ppq=settings.transport.ppq_division)
        self.lanes: Dict[str, Lane] = {}
        seed = settings.spiral.seed
        self.spiral = SpiralWalker(
            scene_count=len(settings.scenes),
            k_step=settings.spiral.k_step,
            memory_k=settings.spiral.memory_k,
            p_jump=settings.spiral.p_jump,
            seed=seed,
        )
        self.current_scene_index = 0
        in_name = in_port_override or settings.midi.in_port_name
        out_name = out_port_override or settings.midi.out_port_name
        self.input_port = MidiInput(in_name, callback=self._on_midi_message, use_virtual=self.virtual_in)
        self.output_port = MidiOutput(out_name, max_messages_per_sec=settings.midi.max_messages_per_sec, dry_run=dry_run, use_virtual=self.virtual_out)
        self._stop_event = threading.Event()
        self._register_division_callbacks()
        self._build_lanes(seed)
        self.last_values: Dict[str, int] = {}
        self.armed = self.arm_ticks == 0
        self._ticks_since_start = 0
        self._log_handle = None
        self._scene_order = self._build_scene_order()
        self._hard_reset_state()

    def _build_scene_order(self) -> List[str]:
        if self.settings.transport.scene_order:
            return self.settings.transport.scene_order
        keys = list(self.settings.scenes.keys())
        # natural sort for names like scene1, scene2, scene10
        def nat_key(k: str) -> List:
            import re
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", k)]

        return sorted(keys, key=nat_key)

    def _build_lanes(self, seed: int | None) -> None:
        for lane_def in self.settings.lanes:
            lane_seed = None if seed is None else hash((lane_def.name, seed)) & 0xFFFFFFFF
            lane = Lane(
                name=lane_def.name,
                cc=lane_def.cc,
                channel=lane_def.channel,
                division=lane_def.division,
                curve=lane_def.curve,
                smoothing=lane_def.smoothing,
                role=lane_def.role,
                shape=lane_def.shape,
                deadband=lane_def.deadband,
                slew_limit=lane_def.slew_limit,
            )
            if lane_seed is not None:
                lane.rng.seed(lane_seed)
            self.lanes[lane.name] = lane

    def _register_division_callbacks(self) -> None:
        divisions = {lane.division for lane in self.settings.lanes}
        for division in divisions:
            self.clock.register_callback(division, lambda bar, quarter, tick, d=division: self._on_division(d, bar, quarter, tick))

    def _on_midi_message(self, message) -> None:
        if message.type == "clock":
            self.clock.handle_message("clock")
            if self.clock.running and not self.armed:
                self._ticks_since_start += 1
                if self._ticks_since_start >= self.arm_ticks:
                    self.armed = True
                    logger.info("Engine armed after %s ticks", self._ticks_since_start)
        elif message.type == "start":
            self.clock.handle_message("start")
            if not self.soft_start:
                self._hard_reset_state()
            self.armed = self.arm_ticks == 0
            self._ticks_since_start = 0
        elif message.type == "stop":
            self.clock.handle_message("stop")
            self.armed = False
        elif message.type == "continue":
            self.clock.start(soft=True)
            if self.arm_ticks == 0:
                self.armed = True
            else:
                self.armed = False
                self._ticks_since_start = 0

    def _scene_for_index(self, idx: int) -> Dict:
        order = self._scene_order
        scene_name = order[idx % len(order)]
        return self.settings.scenes[scene_name]

    def _on_division(self, division: str, bar: int, quarter: int, tick: int) -> None:
        if not self.armed:
            return
        ticks_per_bar = self.clock.ppq * self.clock.bar_quarters
        if tick % ticks_per_bar == 0:
            logger.info("Bar %s Scene %s", bar + 1, self.current_scene_index)
            self._log_bar(bar)
            if not self.freeze_scene and bar and bar % self.settings.transport.phrase_bars == 0:
                self.current_scene_index = self.spiral.on_phrase_boundary()

        scene = self._scene_for_index(self.current_scene_index)
        ordered_lanes = sorted(self.lanes.values(), key=lambda l: 0 if (l.role or "").lower() in {"restraint", "contrast"} else 1)
        for lane in ordered_lanes:
            if lane.division != division:
                continue
            scene_params = scene.get(lane.name)
            if not scene_params:
                continue
            if lane.name in self.frozen_lanes and lane.name in self.last_values:
                continue
            sp = scene_params.__dict__ if hasattr(scene_params, "__dict__") else dict(scene_params)
            adjusted_params = self._apply_meta_to_scene(sp, lane)
            value = lane.next_value(adjusted_params)
            if value is None:
                continue
            self.last_values[lane.name] = value
            self.output_port.send_cc(lane.cc, value, channel=lane.channel)

    def _log_bar(self, bar: int) -> None:
        if not self.session_log_path:
            return
        if self._log_handle is None:
            self._log_handle = self.session_log_path.open("a", encoding="utf-8")
        entry = {
            "timestamp": time.time(),
            "bar": bar,
            "scene_index": self.current_scene_index,
            "frozen_scene": self.freeze_scene,
            "frozen_lanes": sorted(self.frozen_lanes),
            "lanes": self.last_values,
        }
        self._log_handle.write(json.dumps(entry) + "\n")
        self._log_handle.flush()

    def _meta_values(self) -> Dict[str, float]:
        def norm(role: str) -> float:
            for lane in self.lanes.values():
                if (lane.role or "").lower() == role:
                    val = self.last_values.get(lane.name)
                    return (val or 0) / 127.0
            return 0.0

        return {"restraint": norm("restraint"), "contrast": norm("contrast")}

    def _apply_meta_to_scene(self, scene_params: Dict, lane: Lane) -> Dict:
        role = (lane.role or "").lower()
        if role in {"restraint", "contrast"}:
            return scene_params

        meta = self._meta_values()
        scene_min = int(scene_params.get("min", 0))
        scene_max = int(scene_params.get("max", 127))
        midpoint = (scene_min + scene_max) / 2
        half_range = max(1.0, (scene_max - scene_min) / 2)

        restraint = meta["restraint"]
        contrast = meta["contrast"]

        # shrink/expand ranges
        half_range *= (1 - 0.8 * restraint)
        half_range *= (1 + 0.8 * contrast)

        new_min = max(0, int(midpoint - half_range))
        new_max = min(127, int(midpoint + half_range))
        scene_params = dict(scene_params)
        scene_params["min"] = new_min
        scene_params["max"] = new_max
        return scene_params

    def run(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        self.input_port.open()
        self.output_port.open()
        self._stop_event.clear()

        def stop_signal(*_: int) -> None:
            logger.info("Received stop signal, shutting down.")
            self._stop_event.set()
            self.clock.stop()

        signal.signal(signal.SIGINT, stop_signal)
        signal.signal(signal.SIGTERM, stop_signal)

        try:
            while not self._stop_event.is_set():
                time.sleep(0.01)
        finally:
            self.input_port.close()
            self.output_port.close()
            if self._log_handle:
                self._log_handle.close()

    def _hard_reset_state(self) -> None:
        self.clock.reset()
        self.spiral.reset()
        self.current_scene_index = 0
        self.last_values.clear()
        for lane in self.lanes.values():
            lane.reset()
