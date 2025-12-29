import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def _quantile(values: List[int], q: float) -> float:
    if not values:
        return 0
    values = sorted(values)
    k = (len(values) - 1) * q
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def _segment_ranges(bars: List[Dict[str, int]], scene_count: int) -> List[Dict[str, Tuple[int, int]]]:
    if not bars:
        return []
    segment_size = max(1, len(bars) // scene_count)
    scenes: List[Dict[str, Tuple[int, int]]] = []
    for i in range(scene_count):
        start = i * segment_size
        end = (i + 1) * segment_size if i < scene_count - 1 else len(bars)
        segment = bars[start:end]
        lane_values: Dict[str, List[int]] = defaultdict(list)
        for bar in segment:
            for lane, val in bar.items():
                lane_values[lane].append(int(val))
        scene_ranges: Dict[str, Tuple[int, int]] = {}
        for lane, vals in lane_values.items():
            lo = int(_quantile(vals, 0.1))
            hi = int(_quantile(vals, 0.9))
            scene_ranges[lane] = (lo, hi)
        scenes.append(scene_ranges)
    return scenes


def derive_scenes(log_path: str, scene_count: int = 8) -> str:
    bars: List[Dict[str, int]] = []
    for line in Path(log_path).read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        lanes = {k: int(v) for k, v in data.get("lanes", {}).items()}
        bars.append(lanes)

    scenes = _segment_ranges(bars, scene_count=scene_count)
    lines = ["scenes:"]
    for idx, scene in enumerate(scenes, start=1):
        lines.append(f"  scene{idx}:")
        for lane, (lo, hi) in sorted(scene.items()):
            lines.append(f"    {lane}: {{min: {lo}, max: {hi}}}")
    return "\n".join(lines)
