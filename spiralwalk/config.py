import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class TransportConfig:
    phrase_bars: int
    ppq_division: int = 24
    scene_order: list[str] | None = None


@dataclass
class SpiralConfig:
    k_step: int = 5
    memory_k: int = 2
    p_jump: float = 0.08
    seed: int | None = None


@dataclass
class MidiConfig:
    in_port_name: str | None
    out_port_name: str | None
    max_messages_per_sec: int = 200


@dataclass
class LaneDefinition:
    name: str
    cc: int
    channel: int = 0
    division: str = "1/16"
    curve: str = "sine"
    smoothing: float = 0.2
    role: str | None = None
    shape: str = "linear"
    deadband: int = 0
    slew_limit: int | None = None


@dataclass
class SceneDefinition:
    min: int
    max: int
    curve_params: Dict[str, Any] | None = None


@dataclass
class Settings:
    lanes: List[LaneDefinition]
    scenes: Dict[str, Dict[str, SceneDefinition]]
    transport: TransportConfig
    spiral: SpiralConfig
    midi: MidiConfig


def _load_file(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _parse_lane(raw: Dict[str, Any]) -> LaneDefinition:
    return LaneDefinition(
        name=raw["name"],
        cc=int(raw["cc"]),
        channel=int(raw.get("channel", 0)),
        division=str(raw.get("division", "1/16")),
        curve=str(raw.get("curve", "sine")),
        smoothing=float(raw.get("smoothing", 0.2)),
        role=raw.get("role"),
        shape=str(raw.get("shape", "linear")),
        deadband=int(raw.get("deadband", 0)),
        slew_limit=raw.get("slew_limit"),
    )


def _parse_scene(raw: Dict[str, Any]) -> SceneDefinition:
    return SceneDefinition(
        min=int(raw["min"]),
        max=int(raw["max"]),
        curve_params=raw.get("curve_params"),
    )


def load_settings(path: str | Path) -> Settings:
    path = Path(path)
    data = _load_file(path)

    lanes = [_parse_lane(item) for item in data.get("lanes", [])]
    if not lanes:
        raise ValueError("config must define at least one lane")

    scenes_block = data.get("scenes")
    if not scenes_block:
        raise ValueError("config must define scenes")

    scenes: Dict[str, Dict[str, SceneDefinition]] = {}
    for scene_name, lane_map in scenes_block.items():
        scenes[scene_name] = {}
        for lane_name, params in lane_map.items():
            scenes[scene_name][lane_name] = _parse_scene(params)

    transport_raw = data.get("transport", {})
    transport = TransportConfig(
        phrase_bars=int(transport_raw.get("phrase_bars", 8)),
        ppq_division=int(transport_raw.get("ppq_division", 24)),
        scene_order=transport_raw.get("scene_order"),
    )

    spiral_raw = data.get("spiral", {})
    spiral = SpiralConfig(
        k_step=int(spiral_raw.get("k_step", 5)),
        memory_k=int(spiral_raw.get("memory_k", 2)),
        p_jump=float(spiral_raw.get("p_jump", 0.08)),
        seed=spiral_raw.get("seed"),
    )

    midi_raw = data.get("midi", {})
    midi = MidiConfig(
        in_port_name=midi_raw.get("in_port_name"),
        out_port_name=midi_raw.get("out_port_name"),
        max_messages_per_sec=int(midi_raw.get("max_messages_per_sec", 200)),
    )

    return Settings(
        lanes=lanes,
        scenes=scenes,
        transport=transport,
        spiral=spiral,
        midi=midi,
    )
