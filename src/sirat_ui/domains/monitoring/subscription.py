"""A registers.watch subscription, shared by the watch list and the data logger."""

from __future__ import annotations

from typing import List, Optional

from sirat_ui.gateway.call import Call
from sirat_ui.gateway.port import StationGateway
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.app_state import AppState

# registers.watch accepts interval_s from 0.1 to 60 (API doc, registers domain)
WATCH_MIN_S = 0.1
WATCH_MAX_S = 60.0


class WatchSubscription:
    def __init__(self, gateway: StationGateway, state: AppState, errors: ErrorPresenter) -> None:
        self._gateway = gateway
        self._state = state
        self._errors = errors
        self.sub_id: Optional[str] = None

    @property
    def active(self) -> bool:
        return self.sub_id is not None

    def start(self, registers: List[str], interval_s: float, context: str) -> Call:
        self.stop()

        def started(sub_id: str) -> None:
            self.sub_id = sub_id

        return self._gateway.watch(self._state.position, registers, interval_s).then(
            started, lambda e: self._errors.present(e, context))

    def stop(self) -> None:
        if self.sub_id:
            self._gateway.unwatch(self.sub_id)
            self.sub_id = None

    def forget(self) -> None:
        """The station dropped the subscription (e.g. DUT disconnect); don't unwatch it."""
        self.sub_id = None
