"""The bottom dock (History | Actions | Log): open or collapsed to a one-line summary strip, remembered per page.

Collapsed, the strip still shows the last history entry, how many actions are checked, and the newest log line,
so nothing is hidden that the user needs to notice. Watch and Sequences start collapsed: they need the height.
"""

from __future__ import annotations

from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.history.service import HistoryLog
from sirat_ui.domains.logs.service import LogService
from sirat_ui.shared.viewmodel import BaseViewModel, qprop

COLLAPSED_BY_DEFAULT = {"watch", "sequences"}


class DockViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, history: HistoryLog, log: LogService, actions: ActionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._history = history
        self._log = log
        self._actions = actions
        self._page = ""
        self._collapsed_by_page: Dict[str, bool] = {}
        self._collapsed = False
        self._last_history = ""
        self._last_log = ""
        self._last_log_level = "info"
        self._checked = 0
        history.changed.connect(self._refresh)
        log.added.connect(lambda _line: self._refresh())
        log.cleared.connect(self._refresh)
        actions.changed.connect(self._refresh)
        self._refresh()

    collapsed = qprop(bool, "_collapsed", changed)
    page = qprop(str, "_page", changed)
    lastHistory = qprop(str, "_last_history", changed)
    lastLog = qprop(str, "_last_log", changed)
    lastLogLevel = qprop(str, "_last_log_level", changed)
    checkedCount = qprop(int, "_checked", changed)

    def _refresh(self) -> None:
        entries = self._history.entries
        last = entries[-1] if entries else None
        history = f"{last.operation.title()}  {last.target} = 0x{last.value:X}" if last else "No reads or writes yet"
        line = self._log.lines[-1] if self._log.lines else None
        self._update(last_history=history, last_log=line.text if line else "", last_log_level=line.level if line else "info",
                     checked=sum(1 for a in self._actions.actions.values() if a.enabled))

    @pyqtSlot(str)
    def setPage(self, key: str) -> None:  # noqa: N802
        self._update(page=key, collapsed=self._collapsed_by_page.get(key, key in COLLAPSED_BY_DEFAULT))

    @pyqtSlot()
    def toggle(self) -> None:
        self._set_collapsed(not self._collapsed)

    @pyqtSlot()
    def show(self) -> None:
        """Opens the dock (clicking any segment of the strip)."""
        self._set_collapsed(False)

    def _set_collapsed(self, collapsed: bool) -> None:
        self._collapsed_by_page[self._page] = collapsed
        self._update(collapsed=collapsed)
