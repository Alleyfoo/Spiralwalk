import random
from collections import deque
from dataclasses import dataclass


@dataclass
class SpiralState:
    current_scene: int = 0
    bar: int = 0


class SpiralWalker:
    def __init__(self, scene_count: int, k_step: int = 5, memory_k: int = 2, p_jump: float = 0.08, seed: int | None = None):
        self.scene_count = scene_count
        self.k_step = k_step
        self.memory_k = memory_k
        self.p_jump = p_jump
        self.random = random.Random(seed)
        self.state = SpiralState()
        self.history: deque[int] = deque(maxlen=max(1, memory_k))

    def reset(self) -> None:
        self.state = SpiralState()
        self.history.clear()

    def next_scene(self) -> int:
        current = self.state.current_scene
        step = self.k_step % self.scene_count or 1
        candidate = (current + step) % self.scene_count

        if self.random.random() < self.p_jump:
            candidate = self.random.randrange(self.scene_count)

        attempts = self.scene_count
        while attempts and candidate in self.history:
            candidate = (candidate + step) % self.scene_count
            attempts -= 1

        self.history.append(candidate)
        self.state.current_scene = candidate
        return candidate

    def on_phrase_boundary(self) -> int:
        return self.next_scene()
