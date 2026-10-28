"""Advanced page shell: which tool is showing, and the output list model the tools share."""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.advanced.output import OutputLog
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, copy_to_clipboard, qprop

TABS = ["Console", "Custom functions", "DUT control", "Memory"]


class OutputModel(DictListModel):
    """Rows {level, text} mirroring an OutputLog."""

    def __init__(self, log: OutputLog, parent: Optional[QObject] = None) -> None:
        super().__init__(["level", "text"], parent)
        self._log = log
        log.changed.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        self.set_items([{"level": level, "text": text} for level, text in self._log.lines])

    @pyqtSlot()
    def clear(self) -> None:
        self._log.clear()

    @pyqtSlot()
    def copyAll(self) -> None:  # noqa: N802
        copy_to_clipboard(self._log.text())


class AdvancedViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tab = 0

    @pyqtProperty("QStringList", constant=True)
    def tabs(self) -> List[str]:
        return TABS

    tab = qprop(int, "_tab", changed)

    @pyqtSlot(int)
    def setTab(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(TABS):
            self._update(tab=index)

    def show(self, name: str) -> None:
        self.setTab(TABS.index(name))


__all__: List[str] = ["AdvancedViewModel", "OutputModel", "TABS"]
