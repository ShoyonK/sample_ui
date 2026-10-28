"""PrsService (req 24): the chip family's PRS signals, active routes, apply and remove.

Routes aren't persisted (req 24 "No Persistence"); they're cleared when the DUT disconnects. Removing a
route records the register writes it stands for in History, like the original's prs_operation_performed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.core.prs import DISABLE, FALLBACK_SIGNALS, Signal, channel_problem, fallback_signals, removal_ops
from sirat_ui.core.actions import Action
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.history.service import HistoryLog
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.models import PrsRoute, PrsSignalCatalog
from sirat_ui.gateway.port import StationGateway
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.app_state import AppState

_CATEGORY: Dict[str, str] = {name: cat for cat, names in FALLBACK_SIGNALS.items() for name in names}


def prs_op(route: PrsRoute) -> Dict[str, Any]:
    """Req 24 "Action Format"."""
    return {"type": "prs_route", "signal": route.signal, "pin": route.pin, "channel": route.channel}


class PrsService:
    def __init__(self, gateway: StationGateway, state: AppState, history: HistoryLog, actions: ActionService,
                 errors: ErrorPresenter, log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._history = history
        self._actions = actions
        self._errors = errors
        self._log = log
        self.signals: List[Signal] = fallback_signals()
        self.catalog: Optional[PrsSignalCatalog] = None
        self.routes: List[PrsRoute] = []
        self.changed = Event()
        self._was_connected = state.connected
        state.changed.connect(self._on_state)

    @property
    def source_text(self) -> str:
        """Req 24 "Family Indicator"."""
        if self.catalog is None:
            return "Built-in signal list (connect a DUT to load its family's signals)"
        return f"{self.catalog.family.title()} · {self.catalog.module}"

    def _on_state(self, *_: object) -> None:
        connected = self._state.connected
        if connected and not self._was_connected:
            self.load_signals()
        elif not connected and self._was_connected:
            self.routes, self.catalog, self.signals = [], None, fallback_signals()
            self.changed.emit()
        self._was_connected = connected

    def load_signals(self) -> Call[PrsSignalCatalog]:
        """The family's signals, categorized where the name is known; the built-in list if that fails."""
        def loaded(catalog: PrsSignalCatalog) -> None:
            names = [n for n in catalog.signals if n != DISABLE]
            self.catalog = catalog
            self.signals = [Signal(DISABLE)] + [Signal(n, _CATEGORY.get(n, "")) for n in names]
            self.changed.emit()

        def failed(error: ApiError) -> None:
            self._log.warning(f"Couldn't load PRS signals ({error.message}); using the built-in list")

        return self._gateway.prs_signals(self._state.position).then(loaded, failed)

    def problem(self, route: PrsRoute) -> Optional[str]:
        return channel_problem(route.pin, route.channel)

    def apply(self, route: PrsRoute) -> Call[None]:
        """A channel drives one pin and a pin shows one channel, so an older route using either is replaced."""
        def done(_: None) -> None:
            self.routes = [r for r in self.routes if r.channel != route.channel and r.pin != route.pin] + [route]
            self._log.success(f"Routed {route.signal} to {route.pin} via PRS channel {route.channel}")
            self.changed.emit()

        return self._gateway.prs_route(self._state.position, route).then(
            done, lambda e: self._errors.present(e, "PRS route"))

    def remove(self, route: PrsRoute) -> Call[None]:
        def done(_: None) -> None:
            for register, field_name, value in removal_ops(route.pin, route.channel):
                self._history.record("WRITE", register, value, field_name=field_name)
            self.routes = [r for r in self.routes if r != route]
            self._log.info(f"Removed PRS route {route.signal} from {route.pin} (channel {route.channel})")
            self.changed.emit()

        disable = PrsRoute(DISABLE, route.pin, route.channel)
        return self._gateway.prs_route(self._state.position, disable).then(
            done, lambda e: self._errors.present(e, "Remove PRS route"))

    def add_action(self, route: PrsRoute) -> Action:
        name = f"prs_{route.signal.lower()}_{route.pin.lower()}"
        return self._actions.add(self._actions.unique_name(name), [prs_op(route)])
