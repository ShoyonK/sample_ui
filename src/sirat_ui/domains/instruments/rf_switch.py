"""RfSwitchService (req 28): the switch's paths, connect a path to a DUT position, and Add to Actions.

The connected path is the position's rf_path fact (sys.status), so there's nothing to keep here but the paths.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sirat_ui.core.observable import Event
from sirat_ui.domains.automation.recorder import ActionRecorder
from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.port import RfPort
from sirat_ui.models.actions import Action
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState

KIND = "rf_switch"


def rf_switch_op(path: str, position: int) -> Dict[str, Any]:
    """Req 28 "Action Format"."""
    return {"type": "rf_switch", "path": path, "dut_position": position}


class RfSwitchService:
    def __init__(self, gateway: RfPort, state: StationState, bench: InstrumentBench, actions: ActionRecorder,
                 errors: ErrorPresenter, log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._bench = bench
        self._actions = actions
        self._errors = errors
        self._log = log
        self.paths: List[str] = []
        self.changed = Event()
        self._was_connected = False
        state.changed.connect(self._on_state)
        self._on_state()

    def _on_state(self, *_: object) -> None:
        found = self._bench.instrument(KIND)
        connected = bool(found and found.connected)
        if connected and not self._was_connected:
            self.load_paths()
        self._was_connected = connected
        self.changed.emit()

    def current_path(self, position: int) -> str:
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
