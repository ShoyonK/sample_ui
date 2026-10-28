"""Watch list page (req 18): live values, Ctrl/Shift selection, write values, send to the logger."""

from __future__ import annotations

import time
from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.formatting import format_value, parse_value
from sirat_ui.domains.annotations.service import AnnotationService
from sirat_ui.domains.monitoring.logger import DataLoggerService
from sirat_ui.domains.monitoring.subscription import WATCH_MAX_S, WATCH_MIN_S
from sirat_ui.domains.monitoring.watch import WatchService
from sirat_ui.shared.interactions import InteractionService, PromptField, PromptRequest
from sirat_ui.shared.selection import RowSelection
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

ROLES = ["name", "valueText", "enumName", "calcText", "changed", "changedText", "trend", "writable", "selected"]


def _ago(ts, now: float) -> str:
    if ts is None:
        return "—"
    seconds = now - ts
    if seconds < 5:
        return "just now"
    if seconds < 90:
        return f"{int(seconds)} s ago"
    return f"{int(seconds // 60)} min ago"


class WatchListViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, watch: WatchService, logger: DataLoggerService, annotations: AnnotationService,
                 interactions: InteractionService, state: AppState, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._watch = watch
        self._logger = logger
        self._annotations = annotations
        self._interactions = interactions
        self._model = DictListModel(ROLES, self)
        self._selection = RowSelection()
        self._live = False
        self._interval_text = "1.0"
        watch.updated.connect(self._rebuild)
        annotations.changed.connect(self._rebuild)
        state.preferences_changed.connect(lambda _: self._rebuild())  # req 18: format follows main window
        self._rebuild()

    live = qprop(bool, "_live", changed)
    intervalText = qprop(str, "_interval_text", changed)

    @pyqtProperty(int, notify=changed)
    def selectedCount(self) -> int:  # noqa: N802
        return len(self._selection.selected)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    def _rebuild(self) -> None:
        now = time.time()
        fmt = self._state.preferences.format
        self._selection.keep_only(i.name for i in self._watch.items)
        rows = []
        for item in self._watch.items:
            enum = item.field.enum_for(item.value) if (item.field and item.value is not None) else None
            access = item.field.access if item.field else item.register.access
            rows.append({
                "name": item.name,
                "valueText": format_value(item.value, fmt, item.field.width if item.field else item.register.width)
                if item.value is not None else "—",
                "enumName": enum.name if enum else "", "changed": item.changed,
                "calcText": self._annotations.format_calculated(item.name, item.value),
                "changedText": _ago(item.changed_at, now), "trend": list(item.trend),
                "writable": access.writable, "selected": item.name in self._selection,
            })
        self._model.set_items(rows)
        self._update(live=self._watch.live, interval_text=f"{self._watch.interval_s:.1f}")
        self.changed.emit()

    def _selected_names(self) -> List[str]:
        return [i.name for i in self._watch.items if i.name in self._selection]

    # ---- refresh -------------------------------------------------------------------------------

    @pyqtSlot(str)
    def setIntervalText(self, text: str) -> None:  # noqa: N802
        try:
            interval = float(text.replace("s", "").strip())
        except ValueError:
            interval = -1
        if not WATCH_MIN_S <= interval <= WATCH_MAX_S:
            self._interactions.toast("error", f"Enter a refresh rate between {WATCH_MIN_S:g} and {WATCH_MAX_S:g} seconds")
            self._rebuild()
            return
        self._watch.set_interval(interval)

    @pyqtSlot()
    def toggleLive(self) -> None:  # noqa: N802
        if self._watch.live:
            self._watch.stop()
        elif not self._watch.items:
            self._interactions.toast("error", "Add fields from the register view first")
        else:
            self._watch.start()

    @pyqtSlot()
    def refreshOnce(self) -> None:  # noqa: N802
        self._watch.refresh_once()

    # ---- selection -----------------------------------------------------------------------------

    @pyqtSlot(int, str)
    def select(self, row: int, mode: str) -> None:
        name = self._model.get(row).get("name")
        if name:
            self._selection.select([r["name"] for r in self._model.items], name, mode)
            self._rebuild()

    # ---- editing -------------------------------------------------------------------------------

    @pyqtSlot(int)
    def writeValue(self, row: int) -> None:  # noqa: N802
        """Req 18: write a new value for a watched field (double-click or context menu)."""
        item = self._model.get(row)
        name = item.get("name")
        if not name:
            return
        if not item.get("writable"):
            self._interactions.toast("error", f"{name} is read-only")
            return
        fmt = self._state.preferences.format

        def answered(values) -> None:
            if not values:
                return
            try:
                value = parse_value(values.get("value", ""), fmt)
            except ValueError as exc:
                self._interactions.toast("error", str(exc))
                return
            self._watch.write(name, value)

        current = item.get("valueText", "")
        self._interactions.prompt(PromptRequest(f"Write {name}", [
            PromptField("value", f"New value ({fmt.value})", "" if current == "—" else current)],
            confirm_text="Write")).then(answered)

    @pyqtSlot(int)
    def remove(self, row: int) -> None:
        name = self._model.get(row).get("name")
        if name:
            self._watch.remove(name)

    @pyqtSlot()
    def removeSelected(self) -> None:  # noqa: N802
        names = self._selected_names()
        if not names:
            self._interactions.toast("error", "Select the rows to delete")
            return
        for name in names:
            self._watch.remove(name)
        self._selection.clear()

    @pyqtSlot()
    def clearAll(self) -> None:  # noqa: N802
        self._watch.clear()

    # ---- logger --------------------------------------------------------------------------------

    def _send_to_logger(self, names: List[str]) -> None:
        added = sum(1 for name in names if self._logger.track(name))
        self._interactions.toast("info", f"Added {added} field(s) to the data logger")

    @pyqtSlot()
    def addAllToLogger(self) -> None:  # noqa: N802
        self._send_to_logger([i.name for i in self._watch.items])

    @pyqtSlot()
    def addSelectedToLogger(self) -> None:  # noqa: N802
        names = self._selected_names()
        if not names:
            self._interactions.toast("error", "Select the rows to add")
            return
        self._send_to_logger(names)

    @pyqtSlot(int)
    def addRowToLogger(self, row: int) -> None:  # noqa: N802
        name = self._model.get(row).get("name")
        if name:
            self._send_to_logger([name])
