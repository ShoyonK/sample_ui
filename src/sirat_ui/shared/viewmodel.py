"""Shared ViewModel plumbing: a property helper and a generic dict-backed list model."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from PyQt5.QtCore import QAbstractListModel, QModelIndex, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QGuiApplication

from sirat_ui.shared.qt import DISPLAY_ROLE, USER_ROLE, pyqtProperty


def qprop(type_: Any, attr: str, notify: Any) -> pyqtProperty:
    """Read-only Qt property backed by `self.<attr>`. QML changes state through slots, never setters."""
    return pyqtProperty(type_, lambda self: getattr(self, attr), notify=notify)


class BaseViewModel(QObject):
    """Subclasses declare `changed = pyqtSignal()` and use `qprop(..., notify=changed)`."""

    def _update(self, **values: Any) -> None:
        dirty = False
        for name, value in values.items():
            attr = "_" + name
            if getattr(self, attr, object()) != value:
                setattr(self, attr, value)
                dirty = True
        if dirty:
            self.changed.emit()  # type: ignore[attr-defined]


class DictListModel(QAbstractListModel):
    """A list model whose rows are dicts. Role names are the dict keys."""

    countChanged = pyqtSignal()

    def __init__(self, roles: Iterable[str], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._roles = list(roles)
        self._role_ids = {USER_ROLE + 1 + i: name for i, name in enumerate(self._roles)}
        self._items: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 (Qt API)
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = DISPLAY_ROLE) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        name = self._role_ids.get(role)
        return self._items[index.row()].get(name) if name else None

    def roleNames(self) -> Dict[int, bytes]:  # noqa: N802 (Qt API)
        return {role: name.encode() for role, name in self._role_ids.items()}

    @pyqtProperty(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    @pyqtSlot(int, result="QVariantMap")
    def get(self, row: int) -> Dict[str, Any]:
        return dict(self._items[row]) if 0 <= row < len(self._items) else {}

    @property
    def items(self) -> List[Dict[str, Any]]:
        return list(self._items)

    def set_items(self, items: List[Dict[str, Any]]) -> None:
        """Updates rows in place when the row count is unchanged, so views keep scroll and focus."""
        if len(items) == len(self._items):
            for row, item in enumerate(items):
                if item != self._items[row]:
                    self._items[row] = item
                    index = self.index(row)
                    self.dataChanged.emit(index, index)
            return
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
        self.countChanged.emit()


def clock_text(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def copy_to_clipboard(text: str) -> None:
    clipboard = QGuiApplication.clipboard() if QGuiApplication.instance() is not None else None
    if clipboard is not None:
        clipboard.setText(text)


class ConsoleModel(DictListModel):
    """Run output for consoles (Actions, Sequences): time, level, text; newest at the bottom."""

    MAX_LINES = 400

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(["time", "level", "text"], parent)

    def append(self, level: str, text: str) -> None:
        line = {"time": clock_text(time.time()), "level": level, "text": text}
        self.set_items((self.items + [line])[-self.MAX_LINES:])

    @pyqtSlot()
    def clear(self) -> None:
        self.set_items([])
