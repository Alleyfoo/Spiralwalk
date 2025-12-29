import logging
from collections import defaultdict
from typing import Callable, Dict, List

PPQ = 24  # MIDI clocks per quarter note

logger = logging.getLogger(__name__)


def parse_division(division: str, ppq: int = PPQ) -> int:
    """
    Converts musical division "1/4" -> ticks per event.
    Assumes 4/4; 24 ppq -> quarter = 24 ticks.
    """
    if not division.startswith("1/"):
        raise ValueError(f"Unsupported division: {division}")
    denom = int(division.split("/")[1])
    ticks_per_event = int((ppq * 4) / denom)
    if ticks_per_event <= 0:
        raise ValueError(f"Invalid division {division}")
    return ticks_per_event


class ClockFollower:
    def __init__(self, ppq: int = PPQ, bar_quarters: int = 4):
        self.ppq = ppq
        self.bar_quarters = bar_quarters
        self.callbacks: Dict[int, List[Callable[[int, int, int], None]]] = defaultdict(list)
        self.running = False
        self.tick_count = 0
        self.quarter = 0
        self.bar = 0

    def reset(self) -> None:
        self.tick_count = 0
        self.quarter = 0
        self.bar = 0
        logger.debug("Clock reset")

    def register_callback(self, division: str, callback: Callable[[int, int, int], None]) -> None:
        ticks = parse_division(division, ppq=self.ppq)
        self.callbacks[ticks].append(callback)

    def start(self, soft: bool = False) -> None:
        if not soft:
            self.reset()
        self.running = True
        logger.info("Clock started")

    def stop(self) -> None:
        self.running = False
        logger.info("Clock stopped")

    def handle_clock_tick(self) -> None:
        if not self.running:
            return
        self.tick_count += 1

        for ticks, callbacks in self.callbacks.items():
            if self.tick_count % ticks == 0:
                for cb in callbacks:
                    cb(self.bar, self.quarter, self.tick_count)

        if self.tick_count % self.ppq == 0:
            self.quarter += 1
            if self.quarter % self.bar_quarters == 0:
                self.bar += 1
                logger.debug("Bar advanced to %s", self.bar)

    def handle_message(self, message_type: str) -> None:
        if message_type == "start":
            self.start()
        elif message_type == "stop":
            self.stop()
        elif message_type == "clock":
            self.handle_clock_tick()
        else:
            raise ValueError(f"Unknown message_type {message_type}")
