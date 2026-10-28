"""System information panel (req 31): four categories, Refresh, Copy All, auto-refresh on connect."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.connection.service import ConnectionService
from sirat_ui.domains.connection.system_info import copy_text, sections
from sirat_ui.models.station import DutInfo
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, copy_to_clipboard, qprop
from sirat_ui.state.station import StationState


class SystemInfoViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, connection: ConnectionService, state: StationState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._state = state
        self._interactions = interactions
        self._info: Optional[DutInfo] = None
        self._sections = []
        self._tab = 0
        self._status = ""
        self._busy = False
        self._was_connected = state.connected
        state.changed.connect(self._on_state)
        self.refresh()  # shows the "not connected" message when there's no DUT yet

    sections = qprop("QVariantList", "_sections", changed)
    tabIndex = qprop(int, "_tab", changed)
    statusText = qprop(str, "_status", changed)
    busy = qprop(bool, "_busy", changed)

    @pyqtProperty("QVariantList", notify=changed)
    def tabTitles(self):  # noqa: N802
        return [s["title"] for s in self._sections] or ["Chip Information", "Device Information",
                                                         "RPC Information", "Firmware/Application"]

    @pyqtProperty("QVariantList", notify=changed)
    def currentRows(self):  # noqa: N802
        return self._sections[self._tab]["rows"] if 0 <= self._tab < len(self._sections) else []

    def _on_state(self) -> None:
        """Req 31: refresh whenever a DUT connects."""
        connected = self._state.connected
        if connected and not self._was_connected:
            self.refresh()
        elif not connected and self._was_connected:
            self._update(status="DUT not connected. Connect to see its information.")
        self._was_connected = connected

    @pyqtSlot()
    def refresh(self) -> None:
        if not self._state.connected:
            self._update(status="DUT not connected. Connect to see its information.")
            return
        self._update(busy=True, status="Reading DUT information…")

        def ok(info: DutInfo) -> None:
            self._info = info
            data = [{"title": title, "rows": [{"key": k, "value": v} for k, v in rows]}
                    for title, rows in sections(info)]
            self._update(sections=data, busy=False, status=f"DUT {self._state.position} · {info.chip} rev{info.revision}")
            self.changed.emit()

        def failed(error) -> None:
            self._update(busy=False, status=f"Couldn't read DUT information: {error.message}")

        self._connection.dut_info().then(ok, failed)

    @pyqtSlot(int)
    def setTabIndex(self, index: int) -> None:  # noqa: N802
        self._update(tab=index)

    @pyqtSlot()
    def copyAll(self) -> None:  # noqa: N802
        if self._info is None:
            self._interactions.toast("error", "Nothing to copy yet. Connect a DUT and refresh.")
            return
        copy_to_clipboard(copy_text(self._info))
        self._interactions.toast("info", "System information copied")

    def text(self) -> str:
        return copy_text(self._info) if self._info else ""
