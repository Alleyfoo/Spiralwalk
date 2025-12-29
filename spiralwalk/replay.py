import logging
import threading
import time
from typing import Dict, List

from .clock import ClockFollower
from .config import Settings
from .midi_io import MidiInput, MidiOutput

logger = logging.getLogger(__name__)


class TempoReplay:
    def __init__(
        self,
        settings: Settings,
        frames: List[Dict[str, int]],
        virtual: bool = False,
        in_port_override: str | None = None,
        out_port_override: str | None = None,
        arm_ticks: int = 0,
        dry_run: bool = False,
    ):
        self.settings = settings
        self.frames = frames
        self.virtual = virtual
        self.arm_ticks = max(0, arm_ticks)
        self.in_port_override = in_port_override
        self.out_port_override = out_port_override
        self.dry_run = dry_run

        self.clock = ClockFollower(ppq=settings.transport.ppq_division)
        self.clock.register_callback("1/16", self._on_division)

        in_name = in_port_override or settings.midi.in_port_name
        out_name = out_port_override or settings.midi.out_port_name
        self.input_port = MidiInput(in_name, callback=self._on_midi_message, use_virtual=self.virtual)
        self.output_port = MidiOutput(out_name, max_messages_per_sec=settings.midi.max_messages_per_sec, dry_run=self.dry_run, use_virtual=self.virtual)

        self.lane_map = {lane.name: (lane.cc, lane.channel) for lane in settings.lanes}
        self._stop_event = threading.Event()
        self._armed = self.arm_ticks == 0
        self._ticks_since_start = 0
        self._frame_index = 0

    def run(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        if not self.frames:
            logger.warning("No frames to replay.")
            return
        self.input_port.open()
        self.output_port.open()
        self._stop_event.clear()
        try:
            while not self._stop_event.is_set():
                time.sleep(0.01)
        finally:
            self.input_port.close()
            self.output_port.close()

    def _on_midi_message(self, message) -> None:
        if message.type == "clock":
            self.clock.handle_message("clock")
            if self.clock.running and not self._armed:
                self._ticks_since_start += 1
                if self._ticks_since_start >= self.arm_ticks:
                    self._armed = True
                    logger.info("Replay armed after %s ticks", self._ticks_since_start)
        elif message.type == "start":
            self.clock.start()
            self._frame_index = 0
            self._armed = self.arm_ticks == 0
            self._ticks_since_start = 0
        elif message.type == "continue":
            self.clock.start(soft=True)
            if self.arm_ticks == 0:
                self._armed = True
            else:
                self._armed = False
                self._ticks_since_start = 0
        elif message.type == "stop":
            self.clock.stop()
            self._armed = False

    def _on_division(self, bar: int, quarter: int, tick: int) -> None:
        if not self._armed:
            return
        ticks_per_bar = self.clock.ppq * self.clock.bar_quarters
        if tick % ticks_per_bar != 0:
            return
        frame = self.frames[self._frame_index % len(self.frames)]
        logger.info("Replay bar %s frame %s", bar + 1, self._frame_index)
        for lane_name, value in frame.items():
            mapping = self.lane_map.get(lane_name)
            if not mapping:
                continue
            cc, channel = mapping
            self.output_port.send_cc(cc, int(value), channel=channel)
        self._frame_index += 1
