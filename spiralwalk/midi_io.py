import logging
import time
from typing import Callable, Iterable

import mido

logger = logging.getLogger(__name__)


class MidiInput:
    def __init__(self, port_name: str | None, callback: Callable[[mido.Message], None], use_virtual: bool = False):
        self.port_name = port_name
        self.callback = callback
        self.use_virtual = use_virtual
        self._port = None

    def open(self) -> None:
        if self.use_virtual:
            name = self.port_name or "Spiralwalk Virtual In"
            try:
                self._port = mido.open_input(name, virtual=True, callback=self.callback)
                logger.info("Opened virtual MIDI input: %s", name)
            except Exception as exc:
                logger.error("Failed to open virtual MIDI input (%s): %s", name, exc)
                raise
            return

        if not self.port_name:
            logger.warning("No MIDI input port configured; clock will not advance.")
            return
        self._port = mido.open_input(self.port_name, callback=self.callback)
        logger.info("Opened MIDI input: %s", self.port_name)

    def close(self) -> None:
        if self._port:
            self._port.close()
            logger.info("Closed MIDI input")


class MidiOutput:
    def __init__(self, port_name: str | None, max_messages_per_sec: int = 200, dry_run: bool = False, use_virtual: bool = False):
        self.port_name = port_name
        self.max_messages_per_sec = max_messages_per_sec
        self.dry_run = dry_run
        self.use_virtual = use_virtual
        self._port = None
        self._sent_times: list[float] = []

    def open(self) -> None:
        if self.dry_run:
            logger.info("Dry-run: MIDI output disabled")
            return
        if self.use_virtual:
            name = self.port_name or "Spiralwalk Virtual Out"
            try:
                self._port = mido.open_output(name, virtual=True)
                logger.info("Opened virtual MIDI output: %s", name)
            except Exception as exc:
                logger.error("Failed to open virtual MIDI output (%s): %s", name, exc)
                raise
            return
        if not self.port_name:
            logger.warning("No MIDI output port configured.")
            return
        self._port = mido.open_output(self.port_name)
        logger.info("Opened MIDI output: %s", self.port_name)

    def close(self) -> None:
        if self._port:
            self._port.close()
            logger.info("Closed MIDI output")

    def _can_send(self) -> bool:
        now = time.monotonic()
        window_start = now - 1
        self._sent_times = [t for t in self._sent_times if t >= window_start]
        if len(self._sent_times) >= self.max_messages_per_sec:
            return False
        self._sent_times.append(now)
        return True

    def send_cc(self, cc: int, value: int, channel: int = 0) -> None:
        if not self._can_send():
            logger.debug("Rate limit hit; skipping CC %s", cc)
            return
        msg = mido.Message("control_change", control=cc, value=value, channel=channel)
        if self.dry_run or not self._port:
            logger.info("CC ch%s cc%s val%s", channel + 1, cc, value)
            return
        self._port.send(msg)


def list_ports() -> tuple[Iterable[str], Iterable[str]]:
    return mido.get_input_names(), mido.get_output_names()
