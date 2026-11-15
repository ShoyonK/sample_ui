"""ChamberService (req 29): set the temperature, poll the live reading, wait for it to stabilize.

Polling runs only while someone is looking (the Instruments page is visible). "Wait for stable" is an
instrument activity, so it reports progress and can be aborted. Nothing persists (req 29 "No Persistence").
"""

from __future__ import annotations

from typing import List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.domains.instruments.bench import InstrumentBench, InstrumentService
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.port import InstrumentsPort
from sirat_ui.gateway.scheduler import Handle, Scheduler
from sirat_ui.models.station import ActivityFinished, ActivityProgress, ChamberReading
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState

HISTORY = 120   # readings kept for the trend line


class ChamberService(InstrumentService):
    """The temperature chamber: polled reading and trend, setpoint, and the wait-for-stable activity."""

    KIND = "chamber"

    def __init__(self, gateway: InstrumentsPort, state: StationState, bench: InstrumentBench, errors: ErrorPresenter,
                 log: LogService, scheduler: Scheduler) -> None:
        super().__init__(state, bench)
        self._gateway = gateway
        self._errors = errors
        self._log = log
        self._scheduler = scheduler
        self.reading: Optional[ChamberReading] = None
        self.history: List[float] = []
        self.interval_s = 2.0
        self.wait_activity = ""
        self.wait_text = ""
        self.changed = Event()
        self._poll: Optional[Handle] = None
        self._poll_failed = False

    # ---- live reading -----------------------------------------------------------------------------------

    def start_polling(self, interval_s: Optional[float] = None) -> None:
        """Reads now and then every interval_s (the last interval when None) until stop_polling()."""
        if interval_s is not None:
            self.interval_s = interval_s
        self.stop_polling()
        self.read()
        self._poll = self._scheduler.every(int(self.interval_s * 1000), self._poll_once)

    def _poll_once(self) -> None:
        self.read()

    def stop_polling(self) -> None:
        if self._poll is not None:
            self._poll.cancel()
            self._poll = None

    @property
    def polling(self) -> bool:
        return self._poll is not None

    def read(self) -> Call[ChamberReading]:
        """Reads the chamber; without one to read, resolves with the last reading (None before the first)."""
        if not self.can("instruments.chamber.read"):
            # Call is invariant, so Optional here would ripple into every caller of read()
            return Call.succeeded(self.reading)  # type: ignore[arg-type]

        def done(reading: ChamberReading) -> None:
            self._poll_failed = False
            self.reading = reading
            self.history = (self.history + [reading.actual_c])[-HISTORY:]
            self.changed.emit()

        def failed(error: ApiError) -> None:
            if not self._poll_failed:  # one log line per outage, not one per poll
                self._log.warning(f"Couldn't read the chamber ({error.message})")
            self._poll_failed = True

        return self._gateway.chamber_read(self.instrument_id).then(done, failed)

    # ---- setpoint and waiting ------------------------------------------------------------------------------

    def set_temperature(self, celsius: float) -> Call[None]:
        def done(_: None) -> None:
            self._log.success(f"Chamber setpoint {celsius:g} °C")
            self.read()

        return self._gateway.chamber_set_temp(self.instrument_id, celsius).then(
            done, lambda e: self._errors.present(e, "Set temperature"))

    def wait_stable(self, tolerance_c: float, hold_s: float) -> Call[str]:
        """Starts waiting until the reading stays within tolerance for hold_s (an abortable activity)."""
        def started(activity_id: str) -> None:
            self.wait_activity = activity_id
            self.wait_text = "Waiting for the chamber to settle"
            self._bench.follow(activity_id, self._progress, self._finished)
            self.changed.emit()

        return self._gateway.chamber_wait_stable(self.instrument_id, tolerance_c, hold_s).then(
            started, lambda e: self._errors.present(e, "Wait for stable"))

    def abort_wait(self) -> None:
        if self.wait_activity:
            self._bench.abort(self.wait_activity)

    def _progress(self, event: ActivityProgress) -> None:
        self.wait_text = event.message
        self.changed.emit()

    def _finished(self, event: ActivityFinished) -> None:
        self.wait_activity = ""
        if event.ok:
            self.wait_text = "Stable"
        else:
            self.wait_text = "Stopped" if event.error is None else event.error.message
            if event.error is not None:
                self._errors.present(event.error, "Wait for stable")
        self.read()
        self.changed.emit()
