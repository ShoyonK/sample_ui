"""Instruments page, RF switch card (req 28): path and DUT position, Connect / Disconnect, Add to Actions."""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.instruments.instrument_viewmodel import InstrumentViewModel, instrument_properties
from sirat_ui.domains.instruments.rf_switch import KIND, RfSwitchService
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import qprop
from sirat_ui.state.station import StationState

POSITIONS = ["1", "2", "3", "4"]


class RfSwitchViewModel(InstrumentViewModel):
    KIND = KIND
    changed = pyqtSignal()
    instrumentText, instrumentFound, instrumentConnected, errors, errorText = instrument_properties(changed)

    def __init__(self, service: RfSwitchService, bench: InstrumentBench, state: StationState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(bench, state, parent)
        self._service = service
        self._interactions = interactions
        self._path = ""
        self._position = state.position
        self._busy = False
        service.changed.connect(self._refresh)
        self._refresh()

    @pyqtProperty("QStringList", notify=changed)
    def paths(self) -> List[str]:
        return list(self._service.paths)

    @pyqtProperty("QStringList", constant=True)
    def positions(self) -> List[str]:
        return POSITIONS

    @pyqtProperty(int, notify=changed)
    def positionIndex(self) -> int:  # noqa: N802
        return self._position - 1

    busy = qprop(bool, "_busy", changed)

    @pyqtProperty(int, notify=changed)
    def pathIndex(self) -> int:  # noqa: N802
        return self._service.paths.index(self._path) if self._path in self._service.paths else -1

    @pyqtProperty(str, notify=changed)
    def currentPath(self) -> str:  # noqa: N802
        return self._service.current_path(self._position)

    @pyqtProperty(str, notify=changed)
    def currentText(self) -> str:  # noqa: N802
        path = self.currentPath
        return f"DUT {self._position} is on {path}" if path else f"DUT {self._position} has no RF path connected"

    @pyqtProperty(bool, notify=changed)
    def canConnect(self) -> bool:  # noqa: N802
        return bool(self._path) and not self._busy and self._state.can("rf.connect")

    @pyqtProperty(bool, notify=changed)
    def canDisconnect(self) -> bool:  # noqa: N802
        return bool(self.currentPath) and not self._busy and self._state.can("rf.disconnect")

    def _refresh(self) -> None:
        if self._service.paths and self._path not in self._service.paths:
            self._path = self._service.paths[0]
        self.changed.emit()

    @pyqtSlot(int)
    def setPath(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(self._service.paths):
            self._update(path=self._service.paths[index])

    @pyqtSlot(int)
    def setPosition(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(POSITIONS):
            self._update(position=index + 1)

    @pyqtSlot()
    def connectPath(self) -> None:  # noqa: N802
        if not self.canConnect:
            return
        path, position = self._path, self._position
        self._update(busy=True)
        self._service.connect(position, path).then(
            lambda _: (self._update(busy=False),
                       self._interactions.toast("success", f"Connected {path} to DUT {position}")),
            lambda _: self._update(busy=False))

    @pyqtSlot()
    def disconnectPath(self) -> None:  # noqa: N802
        if self.canDisconnect:
            self._service.disconnect(self._position)

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if not self._path:
            return
        action = self._service.add_action(self._path, self._position)
        self._interactions.toast("success", f"Added {action.name} to Actions")


__all__: List[str] = ["RfSwitchViewModel"]
