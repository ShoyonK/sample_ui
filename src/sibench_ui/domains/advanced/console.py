"""ConsoleService (req 20): run Python on the station in the shared session, with history and help.

History lives only in memory (req 20 "No Persistence"). `help` and `help()` show the session's names
instead of starting Python's interactive help, which would wait for input that never comes.
"""

from __future__ import annotations

from typing import List

from sibench_ui.core.console import WELCOME, CommandHistory, echo, help_lines, result_lines
from sibench_ui.core.observable import Event
from sibench_ui.domains.advanced.output import OutputLog
from sibench_ui.domains.advanced.session import PythonSession
from sibench_ui.gateway.errors import ApiError
from sibench_ui.gateway.port import AdvancedPort
from sibench_ui.models.station import ExecResult, NameInfo
from sibench_ui.shared.error_presenter import ErrorPresenter
from sibench_ui.state.station import StationState


class ConsoleService:
    """The Python console: runs commands in the shared PythonSession, one at a time, with output and history."""

    def __init__(self, gateway: AdvancedPort, state: StationState, session: PythonSession,
                 errors: ErrorPresenter) -> None:
        self._gateway = gateway
        self._state = state
        self._session = session
        self._errors = errors
        self.history = CommandHistory()
        self.output = OutputLog()
        self.output.add(WELCOME)
        self.busy = False
        self.changed = Event()
        session.ended.connect(lambda reason: self.output.line("note", reason))

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.changed.emit()

    def run(self, code: str) -> None:
        """Runs one command (ignored while another runs). `help` shows the session's names instead."""
        if self.busy or not code.strip():
            return
        self.history.add(code)
        self.output.add(echo(code))
        if code.strip() in ("help", "help()"):
            self.show_help()
            return
        self._set_busy(True)

        def done(result: ExecResult) -> None:
            self._set_busy(False)
            self.output.add(result_lines(result.stdout, result.stderr, result.result_text,
                                         result.error.text if result.error else None))

        def failed(error: ApiError) -> None:
            self._set_busy(False)
            self.output.line("error", self._errors.message_for(error))

        self._session.with_session(lambda sid: self._gateway.console_exec(sid, code)).then(done, failed)

    def show_help(self) -> None:
        def done(names: List[NameInfo]) -> None:
            self.output.add(help_lines([(n.name, n.type, n.doc) for n in names]))

        def offline(_: object = None) -> None:   # also the error callback: without the names, show the basics
            self.output.add(help_lines([("dut", "DUT", "available once a DUT is connected")]))

        if not self._state.connected:
            offline()
            return
        self._session.with_session(self._gateway.console_names).then(done, offline)

    def restart(self) -> None:
        self._session.restart()
