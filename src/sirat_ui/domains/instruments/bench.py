"""InstrumentBench: which instruments the station has, connecting them, and following their activities.

Instrument facts arrive with sys.status (StationState.instruments). Chamber waits and ECA captures are activities that
belong to an instrument (instrument_id, no position); follow() hands them to the shared ActivityTracker.
"""

from __future__ import annotations

from typing import Any, Optional

from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.activities import ActivityTracker, Done, Progress
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.port import InstrumentsPort
from sirat_ui.models.facts import InstrumentFacts
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState

KIND_NAMES = {"signal_generator": "signal generator", "rf_switch": "RF switch", "chamber": "temperature chamber",
              "eca": "ECA"}


class InstrumentBench:
    """The station's instruments as the cards see them (StationState.instruments), and their activities."""

    def __init__(self, gateway: InstrumentsPort, state: StationState, activities: ActivityTracker, errors: ErrorPresenter,
                 log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._activities = activities
        self._errors = errors
        self._log = log

    def instrument(self, kind: str) -> Optional[InstrumentFacts]:
        """The bench's instrument of that kind: the first connected one, else the first one listed."""
        return self._state.instrument(kind)

    def instrument_id(self, kind: str) -> str:
        found = self._state.instrument(kind)
        return found.id if found else ""

    def describe(self, kind: str) -> str:
        """The status line each instrument card shows."""
        found = self._state.instrument(kind)
        name = KIND_NAMES.get(kind, kind)
        if found is None:
            return f"No {name} on this station"
        model = f"{found.model} · " if found.model else ""
        if not found.connected:
            return f"{model}{found.id} isn't connected"
        busy = f", {found.activity}" if found.activity != "idle" else ""
        return f"{model}{found.id}{busy}"

    def connect(self, kind: str) -> Call[None]:
        """Reconnects the instrument of that kind (the Connect button on a dropped instrument's card)."""
        instrument_id = self.instrument_id(kind)
        return self._gateway.connect_instrument(instrument_id).then(
            None, lambda e: self._errors.present(e, f"Connect {instrument_id}"))

    # ---- activities ------------------------------------------------------------------------------------

    def follow(self, activity_id: str, on_progress: Progress, on_done: Done) -> None:
        self._activities.follow(activity_id, on_progress, on_done)

    def abort(self, activity_id: str) -> Call[Any]:
        return self._gateway.abort_activity(activity_id)


class InstrumentService:
    """What every instrument service shares: which instrument it drives, its requires checks, and noticing when
    that instrument connects or drops.

    Subclasses set KIND, call _watch_connection() at the end of __init__, and override _connection_changed.
    """

    KIND = ""

    def __init__(self, state: StationState, bench: InstrumentBench) -> None:
        self._state = state
        self._bench = bench
        self._was_connected = False

    @property
    def instrument_id(self) -> str:
        return self._bench.instrument_id(self.KIND)

    def can(self, method: str) -> bool:
        """Whether `method` may be called on this service's instrument right now."""
        return bool(self.instrument_id) and self._state.can(method, self.instrument_id)

    def _watch_connection(self) -> None:
        self._state.changed.connect(self._on_state)
        self._on_state()

    def _on_state(self) -> None:
        found = self._bench.instrument(self.KIND)
        connected = bool(found and found.connected)
        was, self._was_connected = self._was_connected, connected
        self._connection_changed(connected, was)

    def _connection_changed(self, connected: bool, was_connected: bool) -> None:
        """Called on every state change with the instrument's connection now and before."""
