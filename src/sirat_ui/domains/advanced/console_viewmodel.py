"""Advanced page, Console tab (req 20): output, the input draft with history, Execute, Help, Clear."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.advanced.advanced_viewmodel import OutputModel
from sirat_ui.domains.advanced.console import ConsoleService
from sirat_ui.domains.advanced.session import PythonSession
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, qprop
from sirat_ui.state.station import StationState


class ConsoleViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: ConsoleService, session: PythonSession, state: StationState,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._session = session
        self._state = state
        self._draft = ""
        self._output = OutputModel(service.output, self)
        service.changed.connect(self.changed.emit)
        service.output.changed.connect(self.changed.emit)   # the session line follows the output
        state.changed.connect(self.changed.emit)

    @pyqtProperty(QObject, constant=True)
    def output(self) -> QObject:
        return self._output

    draft = qprop(str, "_draft", changed)

    @pyqtProperty(bool, notify=changed)
    def busy(self) -> bool:
        return self._service.busy

    @pyqtProperty(bool, notify=changed)
    def connected(self) -> bool:
        return self._state.connected

    @pyqtProperty(str, notify=changed)
    def sessionText(self) -> str:  # noqa: N802
        if not self._state.connected:
            return f"DUT {self._state.position} isn't connected"
        if self._session.open:
            return f"Session on DUT {self._session.position} · variables persist until you restart it"
        return f"DUT {self._state.position} · a session starts with the first command"

    @pyqtSlot(str)
    def setDraft(self, text: str) -> None:  # noqa: N802
        self._update(draft=text)

    @pyqtSlot()
    def execute(self) -> None:
        code = self._draft
        if code.strip() and not self._service.busy:
            self._update(draft="")
            self._service.run(code)

    @pyqtSlot()
    def historyPrevious(self) -> None:  # noqa: N802
        command = self._service.history.previous()
        if command is not None:
            self._update(draft=command)

    @pyqtSlot()
    def historyNext(self) -> None:  # noqa: N802
        command = self._service.history.next()
        if command is not None:
            self._update(draft=command)

    @pyqtSlot()
    def help(self) -> None:
        self._service.show_help()

    @pyqtSlot()
    def restart(self) -> None:
        self._service.restart()
        self.changed.emit()
