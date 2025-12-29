import math
import random
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LaneState:
    previous_value: Optional[float] = None
    phase: float = 0.0
    hold_value: float = 0.0
    hold_remaining: int = 0
    random_position: float = 0.5
    last_output: Optional[int] = None


@dataclass
class Lane:
    name: str
    cc: int
    channel: int
    division: str
    curve: str
    smoothing: float
    role: str | None = None
    shape: str = "linear"
    deadband: int = 0
    slew_limit: int | None = None
    rng: random.Random = field(default_factory=random.Random)
    state: LaneState = field(default_factory=LaneState)

    def _normalize(self, value: float, scene_min: int, scene_max: int) -> int:
        value = max(0.0, min(1.0, value))
        scaled = scene_min + (scene_max - scene_min) * value
        return int(round(max(0, min(127, scaled))))

    def _curve_value(self, scene_params: Dict) -> float:
        curve_params = scene_params.get("curve_params") or {}
        curve = self.curve
        state = self.state

        if curve == "sine":
            cycle_steps = max(1, int(curve_params.get("cycle_steps", 16)))
            state.phase += 2 * math.pi / cycle_steps
            return 0.5 * (1 + math.sin(state.phase))

        if curve == "ramp":
            cycle_steps = max(1, int(curve_params.get("cycle_steps", 16)))
            step = (state.phase + 1) % cycle_steps
            state.phase = step
            return step / (cycle_steps - 1 if cycle_steps > 1 else 1)

        if curve == "random_walk":
            step_size = float(curve_params.get("step_size", 0.08))
            delta = self.rng.uniform(-step_size, step_size)
            state.random_position = max(0.0, min(1.0, state.random_position + delta))
            return state.random_position

        if curve == "step_hold":
            hold_steps = max(1, int(curve_params.get("hold_steps", 4)))
            if state.hold_remaining <= 0:
                state.hold_value = self.rng.random()
                state.hold_remaining = hold_steps
            state.hold_remaining -= 1
            return state.hold_value

        # default fallback
        return self.rng.random()

    def _apply_shape(self, value: float) -> float:
        value = max(0.0, min(1.0, value))
        shape = (self.shape or "linear").lower()
        if shape == "exp":
            return value ** 2
        if shape == "log":
            return value ** 0.5
        if shape == "s_curve":
            return 0.5 * (1 - math.cos(math.pi * value))
        return value

    def reset(self) -> None:
        self.state = LaneState()

    def next_value(self, scene_params: Dict) -> int | None:
        scene_min = int(scene_params.get("min", 0))
        scene_max = int(scene_params.get("max", 127))
        raw_value = self._curve_value(scene_params)

        if self.state.previous_value is None:
            smoothed = raw_value
        else:
            alpha = max(0.0, min(1.0, self.smoothing))
            smoothed = alpha * raw_value + (1 - alpha) * self.state.previous_value

        self.state.previous_value = smoothed
        shaped = self._apply_shape(smoothed)
        scaled = self._normalize(shaped, scene_min, scene_max)

        if self.state.last_output is not None:
            delta = scaled - self.state.last_output
            if self.deadband and abs(delta) < self.deadband:
                return None
            if self.slew_limit is not None and self.slew_limit >= 0 and abs(delta) > self.slew_limit:
                step = self.slew_limit if delta > 0 else -self.slew_limit
                scaled = self.state.last_output + step

        self.state.last_output = scaled
        return scaled
