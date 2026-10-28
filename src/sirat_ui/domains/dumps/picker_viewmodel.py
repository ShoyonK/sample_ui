"""The peripheral picker dialog (req 12 Take a dump, req 21 Radio Calculator diff): a checklist and a start button.

Whoever opens it supplies the wording, the labels and what Start does, so the picker knows nothing about dumps.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop


class PeripheralPickerViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._peripherals = DictListModel(["name", "label", "checked"], self)
        self._names: List[str] = []
        self._checked: Dict[str, bool] = {}
        self._label: Callable[[str], str] = str
        self._on_start: Callable[[List[str]], None] = lambda names: None
        self._picker_mode = ""
        self._picker_title = self._picker_message = self._picker_confirm = ""
        self._picker_open = False
        self._checked_count = 0

    @pyqtProperty(QObject, constant=True)
    def peripherals(self) -> QObject:
        return self._peripherals

    pickerMode = qprop(str, "_picker_mode", changed)       # "dump" | "radio"
    pickerTitle = qprop(str, "_picker_title", changed)
    pickerMessage = qprop(str, "_picker_message", changed)
    pickerConfirm = qprop(str, "_picker_confirm", changed)
    pickerOpen = qprop(bool, "_picker_open", changed)
    checkedCount = qprop(int, "_checked_count", changed)

    def open(self, mode: str, wording: tuple, checked: Dict[str, bool], label: Callable[[str], str],
             on_start: Callable[[List[str]], None]) -> None:
        title, message, confirm = wording
        self._names, self._checked = list(checked), dict(checked)
        self._label, self._on_start = label, on_start
        self._update(picker_mode=mode, picker_title=title, picker_message=message, picker_confirm=confirm,
                     picker_open=True)
        self._rebuild()

    def checked(self) -> Dict[str, bool]:
        return dict(self._checked)

    def _rebuild(self) -> None:
        self._peripherals.set_items([{"name": n, "label": self._label(n), "checked": self._checked[n]}
                                     for n in self._names])
        self._update(checked_count=sum(self._checked.values()))

    @pyqtSlot()
    def closePicker(self) -> None:  # noqa: N802
        self._update(picker_open=False)

    @pyqtSlot(int)
    def togglePeripheral(self, row: int) -> None:  # noqa: N802
        if 0 <= row < len(self._names):
            name = self._names[row]
            self._checked[name] = not self._checked[name]
            self._rebuild()

    @pyqtSlot()
    def selectAll(self) -> None:  # noqa: N802
        self._checked = {name: True for name in self._names}
        self._rebuild()

    @pyqtSlot()
    def selectNone(self) -> None:  # noqa: N802
        self._checked = {name: False for name in self._names}
        self._rebuild()

    @pyqtSlot()
    def startPicked(self) -> None:  # noqa: N802
        """The Dump / Compare button."""
        chosen = [name for name in self._names if self._checked[name]]
        if chosen:
            self._update(picker_open=False)
            self._on_start(chosen)
