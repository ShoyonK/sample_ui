"""RfSwitchService (req 28): the switch's paths, connect a path to a DUT position, and Add to Actions.

The connected path is the position's rf_path fact (sys.status), so there's nothing to keep here but the paths.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sibench_ui.core.observable import Event
from sibench_ui.domains.automation.recorder import ActionRecorder
from sibench_ui.domains.instruments.bench import InstrumentBench, InstrumentService
from sibench_ui.domains.logs.service import LogService
from sibench_ui.gateway.call import Call
from sibench_ui.gateway.port import RfPort
from sibench_ui.models.actions import Action
from sibench_ui.shared.error_presenter import ErrorPresenter
from sibench_ui.state.station import StationState



def rf_switch_op(path: str, position: int) -> Dict[str, Any]:
    """Req 28 "Action Format"."""
    return {"type": "rf_switch", "path": path, "dut_position": position}


class RfSwitchService(InstrumentService):
    """The RF switch: its paths (loaded when it connects), connect/disconnect a DUT position, Add to Actions."""

    KIND = "rf_switch"

    def __init__(self, gateway: RfPort, state: StationState, bench: InstrumentBench, actions: ActionRecorder,
                 errors: ErrorPresenter, log: LogService) -> None:
        super().__init__(state, bench)
        self._gateway = gateway
        self._actions = actions
        self._errors = errors
        self._log = log
        self.paths: List[str] = []
        self.changed = Event()
        self._watch_connection()

    def _connection_changed(self, connected: bool, was_connected: bool) -> None:
        if connected and not was_connected:
            self.load_paths()
        self.changed.emit()

    def current_path(self, position: int) -> str:
        """The path connected to that position, or ""."""
        return self._state.facts_for(position).rf_path or ""

    def load_paths(self) -> Call[List[str]]:
        def loaded(names: List[str]) -> None:
            self.paths = list(names)
            self.changed.emit()

        return self._gateway.rf_paths().then(loaded, lambda e: self._log.warning(
            f"Couldn't load the RF switch paths ({e.message})"))

    def connect(self, position: int, path: str) -> Call[None]:
        return self._gateway.rf_connect(position, path).then(
            lambda _: self._log.success(f"Connected {path} to DUT {position}"),
            lambda e: self._errors.present(e, "Connect path"))

    def disconnect(self, position: int) -> Call[None]:
        return self._gateway.rf_disconnect(position).then(
            lambda _: self._log.info(f"Disconnected the RF path from DUT {position}"),
            lambda e: self._errors.present(e, "Disconnect path"))

    def add_action(self, path: str, position: int) -> Action:
        return self._actions.add(f"rf_{path.lower()}", [rf_switch_op(path, position)])
