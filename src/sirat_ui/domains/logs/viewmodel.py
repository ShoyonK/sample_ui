"""Log panel (req 35): level checkboxes, case-insensitive search with next/previous, save, pop-out."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.models import LogLine
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.shared.qt import pyqtProperty

LEVELS = ["debug", "info", "warning", "error"]
LEVEL_LABELS = ["Debug", "Info", "Warning", "Error"]
_GROUP = {"debug": "debug", "info": "info", "success": "info", "warning": "warning", "error": "error"}
VISIBLE_LINES = 1000


def format_line(line: LogLine) -> str:
    """Req 35 display format: [14:23:45.123] [INFO] message"""
    stamp = dt.datetime.fromtimestamp(line.ts)
    level = _GROUP.get(line.level, "info").upper()
    return f"[{stamp:%H:%M:%S}.{stamp.microsecond // 1000:03d}] [{level}] {line.text}"


class LogViewModel(BaseViewModel):
    changed = pyqtSignal()
    currentMatchMoved = pyqtSignal(int)  # row to scroll to

    def __init__(self, log: LogService, interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._log = log
        self._interactions = interactions
        self._model = DictListModel(["text", "level", "match", "current"], self)
        self._enabled: Dict[str, bool] = {level: True for level in LEVELS}
        self._search = ""
        self._matches: List[int] = []
        self._current = -1
        self._popped_out = False
        self._match_text = ""
        log.added.connect(lambda _: self._rebuild())
        log.cleared.connect(self._rebuild)
        self._rebuild()

    searchText = qprop(str, "_search", changed)
    matchText = qprop(str, "_match_text", changed)
    poppedOut = qprop(bool, "_popped_out", changed)

    @pyqtProperty("QVariantList", notify=changed)
    def levelStates(self):  # noqa: N802
        return [self._enabled[level] for level in LEVELS]

    @pyqtProperty("QVariantList", constant=True)
    def levelLabels(self):  # noqa: N802
        return LEVEL_LABELS

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    def _rebuild(self) -> None:
        query = self._search.lower()
        lines = [line for line in self._log.lines if self._enabled[_GROUP.get(line.level, "info")]][-VISIBLE_LINES:]
        texts = [format_line(line) for line in lines]
        self._matches = [i for i, text in enumerate(texts) if query and query in text.lower()]
        if self._current >= len(self._matches):
            self._current = len(self._matches) - 1
        if self._matches and self._current < 0:
            self._current = len(self._matches) - 1  # start at the newest match
        current_row = self._matches[self._current] if self._matches else -1
        self._model.set_items([{"text": text, "level": line.level, "match": i in self._matches,
                                "current": i == current_row} for i, (line, text) in enumerate(zip(lines, texts))])
        if not query:
            match_text = ""
        elif not self._matches:
            match_text = "no matches"
        else:
            match_text = f"{self._current + 1} of {len(self._matches)}"
        self._update(match_text=match_text)
        self.changed.emit()

    # ---- filters and search ----------------------------------------------------------------------

    @pyqtSlot(int)
    def toggleLevel(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(LEVELS):
            level = LEVELS[index]
            self._enabled[level] = not self._enabled[level]
            self._rebuild()

    @pyqtSlot(str)
    def setSearchText(self, text: str) -> None:  # noqa: N802
        self._search = text
        self._current = -1
        self._rebuild()
        self._announce()

    @pyqtSlot()
    def nextMatch(self) -> None:  # noqa: N802
        self._step(1)

    @pyqtSlot()
    def previousMatch(self) -> None:  # noqa: N802
        self._step(-1)

    def _step(self, delta: int) -> None:
        if not self._matches:
            return
        self._current = (self._current + delta) % len(self._matches)
        self._rebuild()
        self._announce()

    def _announce(self) -> None:
        if self._matches:
            self.currentMatchMoved.emit(self._matches[self._current])

    # ---- save, clear, pop-out --------------------------------------------------------------------

    @pyqtSlot()
    def saveLog(self) -> None:  # noqa: N802
        """Req 35 "Save Log": every line (not just the filtered ones) in the display format."""
        lines = [format_line(line) for line in self._log.lines]

        def chosen(path) -> None:
            if not path:
                return
            try:
                Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
                self._interactions.toast("success", f"Saved {len(lines)} log lines to {path}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save: {exc}")

        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._interactions.choose_save_file("Save log", f"sirat_log_{stamp}.log", "Log files (*.log *.txt)").then(chosen)

    @pyqtSlot()
    def clear(self) -> None:
        self._log.clear()

    @pyqtSlot(bool)
    def setPoppedOut(self, on: bool) -> None:  # noqa: N802
        self._update(popped_out=on)
