"""PythonSession: the one station-side Python namespace the console and custom functions share (req 15, 20).

It opens lazily on the first run, follows the selected DUT position, and ends when that DUT disconnects
(the station drops it then too). `ended` says why, so the console can tell the user their variables are gone.
"""

from __future__ import annotations

from typing import Callable, Optional, TypeVar

from sirat_ui.core.observable import Event
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.port import AdvancedPort
from sirat_ui.state.station import StationState

T = TypeVar("T")


class PythonSession:
    def __init__(self, gateway: AdvancedPort, state: StationState) -> None:
        self._gateway = gateway
        self._state = state
        self.session_id = ""
        self.position = 0
        self._opening: Optional[Call[str]] = None
        self.ended = Event()    # (reason)
        state.changed.connect(self._on_state)

    @property
    def open(self) -> bool:
        return bool(self.session_id)

    def ensure(self) -> Call[str]:
        if self.session_id and self.position == self._state.position:
            return Call.succeeded(self.session_id)
        if self._opening is not None and self._opening.pending:
            return self._opening
        position = self._state.position

        def opened(session_id: str) -> None:
            self.session_id, self.position = session_id, position

        self._opening = self._gateway.console_open(position).then(opened)
        return self._opening

    def with_session(self, run: Callable[[str], Call[T]]) -> Call[T]:
        """Runs `run(session_id)`, reopening once if the station says the session has ended."""
        out: Call[T] = Call()

        def attempt(retry: bool) -> None:
            def failed(error: ApiError) -> None:
                if retry and error.code == ErrorCode.NOT_FOUND and "session_id" in error.data:
                    self._drop("The session ended on the station; started a new one (earlier variables are gone)")
                    attempt(False)
                else:
                    out.reject(error)
            self.ensure().then(lambda sid: run(sid).then(out.resolve, failed), out.reject)

        attempt(True)
        return out

    def restart(self) -> None:
        if self.session_id:
            self._gateway.console_close(self.session_id)
        self._drop("Session restarted; variables cleared")

    def _drop(self, reason: str) -> None:
        had = bool(self.session_id)
        self.session_id, self.position, self._opening = "", 0, None
        if had:
            self.ended.emit(reason)

    def _on_state(self) -> None:
        if not self.session_id:
            return
        if not self._state.facts_for(self.position).dut_connected:
            self._drop(f"DUT {self.position} disconnected; the session ended and its variables are gone")
        elif self._state.position != self.position:
            self._gateway.console_close(self.session_id)
            self._drop(f"Switched to DUT {self._state.position}; a new session starts on the next run")
