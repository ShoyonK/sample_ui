"""OutputLog: the lines one Advanced tool shows (console, custom functions, DUT control), capped."""

from __future__ import annotations

from typing import Iterable, List

from sirat_ui.core.console import Line
from sirat_ui.core.observable import Event

MAX_LINES = 1000


class OutputLog:
    def __init__(self) -> None:
        self.lines: List[Line] = []
        self.changed = Event()

    def add(self, lines: Iterable[Line]) -> None:
        self.lines = (self.lines + list(lines))[-MAX_LINES:]
        self.changed.emit()

    def line(self, level: str, text: str) -> None:
        self.add([(level, text)])

    def clear(self) -> None:
        self.lines = []
        self.changed.emit()

    def text(self) -> str:
        return "\n".join(text for _, text in self.lines)
