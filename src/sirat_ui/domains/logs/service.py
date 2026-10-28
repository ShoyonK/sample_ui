"""In-app log (req §35). Mirrors every line to Python logging, which writes the session log file."""

from __future__ import annotations

import logging
import time
from typing import Callable, List

from sirat_ui.core.observable import Event
from sirat_ui.gateway.models import LogLine

_PY_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "success": logging.INFO,
              "warning": logging.WARNING, "error": logging.ERROR}
MAX_LINES = 2000


class LogService:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.lines: List[LogLine] = []
        self.added = Event()    # (LogLine)
        self.cleared = Event()
        self._clock = clock
        self._py = logging.getLogger("SiRAT")

    def add(self, level: str, text: str, source: str = "ui") -> None:
        line = LogLine(self._clock(), level, source, text)
        self.lines.append(line)
        if len(self.lines) > MAX_LINES:
            del self.lines[: len(self.lines) - MAX_LINES]
        self._py.log(_PY_LEVELS.get(level, logging.INFO), "[%s] %s", source, text)
        self.added.emit(line)

    def debug(self, text: str) -> None:
        self.add("debug", text)

    def info(self, text: str) -> None:
        self.add("info", text)

    def success(self, text: str) -> None:
        self.add("success", text)

    def warning(self, text: str) -> None:
        self.add("warning", text)

    def error(self, text: str) -> None:
        self.add("error", text)

    def clear(self) -> None:
        self.lines.clear()
        self.cleared.emit()

    def on_gateway_event(self, event: object) -> None:
        if isinstance(event, LogLine):
            self.add(event.level, event.text, event.source)
