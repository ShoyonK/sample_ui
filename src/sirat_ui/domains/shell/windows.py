"""Pop-out windows: any page from the nav rail, the watch list, the data logger, or one logger graph in its own
window. QML creates one Window per row of `model`; closing a window brings its content back to the main window.

Window keys: "page:<key>", "watchList", "logger", "graph:<field name>".
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.shell.pages import PAGES
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel

PAGE, WATCH_LIST, LOGGER, GRAPH = "page", "watchList", "logger", "graph"
_SINGLE_TITLES = {WATCH_LIST: "Watch list", LOGGER: "Data logger"}


def window_key(kind: str, arg: str = "") -> str:
    return f"{kind}:{arg}" if kind in (PAGE, GRAPH) else kind


class WindowsViewModel(BaseViewModel):
    changed = pyqtSignal()
    raiseRequested = pyqtSignal(str)  # key: bring that window to the front

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._model = DictListModel(["key", "kind", "arg", "title"], self)
        self._open: Dict[str, Dict[str, str]] = {}

    @pyqtProperty(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @pyqtProperty("QStringList", notify=changed)
    def openKeys(self) -> List[str]:  # noqa: N802
        return list(self._open)

    def _title(self, kind: str, arg: str) -> Optional[str]:
        if kind == PAGE:
            return next((p["title"] for p in PAGES if p["key"] == arg), None)
        if kind == GRAPH:
            return f"Graph · {arg}" if arg else None
        return _SINGLE_TITLES.get(kind)

    @pyqtSlot(str, str)
    def open(self, kind: str, arg: str = "") -> None:
        """Opens the window, or brings it to the front if it's already open."""
        key = window_key(kind, arg)
        if key in self._open:
            self.raiseRequested.emit(key)
            return
        title = self._title(kind, arg)
        if title is None:
            return
        self._open[key] = {"key": key, "kind": kind, "arg": arg, "title": title}
        self._publish()

    @pyqtSlot(str)
    def close(self, key: str) -> None:
        """Closing a window docks its content back into the main window."""
        if self._open.pop(key, None) is not None:
            self._publish()

    @pyqtSlot(str)
    def show(self, key: str) -> None:
        if key in self._open:
            self.raiseRequested.emit(key)

    @pyqtSlot(str, str, result="bool")
    def isOpen(self, kind: str, arg: str = "") -> bool:  # noqa: N802
        return window_key(kind, arg) in self._open

    @pyqtSlot(str, str, result="QString")
    def keyFor(self, kind: str, arg: str = "") -> str:  # noqa: N802
        return window_key(kind, arg)

    @pyqtSlot()
    def closeAll(self) -> None:  # noqa: N802
        self._open.clear()
        self._publish()

    def _publish(self) -> None:
        self._model.set_items(list(self._open.values()))
        self.changed.emit()

    def open_keys(self) -> List[str]:
        return list(self._open)
