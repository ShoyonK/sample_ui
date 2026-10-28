"""Data logger (req 17): samples tracked fields over time.

Sample rates from 0.01 to 3600 s are allowed. registers.watch only accepts 0.1 to 60 s, so rates
inside that range ride on a watch subscription (one batched event per interval, as the API doc
intends) and rates outside it fall back to polling registers.read_many on a client timer.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.domains.annotations.service import AnnotationService
from sirat_ui.domains.monitoring.subscription import WATCH_MAX_S, WATCH_MIN_S, WatchSubscription
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.port import RegistersPort
from sirat_ui.gateway.scheduler import Handle, Scheduler
from sirat_ui.models.registers import FieldDef, RegisterDef
from sirat_ui.models.station import ReadManyItem, WatchValues
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState
from sirat_ui.stores.formats import read_data_logger, write_data_logger
from sirat_ui.stores.json_store import JsonStore

RATE_MIN_S = 0.01
RATE_MAX_S = 3600.0
MAX_POINTS = 5000  # per series, so long runs don't grow without bound


@dataclass
class Series:
    name: str
    register: RegisterDef
    field: Optional[FieldDef]
    unit: str = ""
    samples: List[int] = field(default_factory=list)   # sample number of each value
    times: List[float] = field(default_factory=list)   # seconds since recording started
    values: List[float] = field(default_factory=list)  # calculated value when a formula exists, else raw


def clamp_rate(rate_s: float) -> float:
    return max(RATE_MIN_S, min(RATE_MAX_S, rate_s))


def uses_watch(rate_s: float) -> bool:
    return WATCH_MIN_S <= rate_s <= WATCH_MAX_S


class DataLoggerService:
    def __init__(self, gateway: RegistersPort, state: StationState, catalog: RegisterCatalog,
                 annotations: AnnotationService, store: JsonStore, errors: ErrorPresenter,
                 scheduler: Scheduler, clock: Callable[[], float] = time.time) -> None:
        self._gateway = gateway
        self._state = state
        self._catalog = catalog
        self._annotations = annotations
        self._store = store
        self._errors = errors
        self._scheduler = scheduler
        self._clock = clock
        self._sub = WatchSubscription(gateway, state, errors)
        self._poll: Optional[Handle] = None
        self.saved_names, rate = read_data_logger(store.load())
        self.rate_s = clamp_rate(rate)
        self.series: List[Series] = []
        self.sample_count = 0
        self.t0: Optional[float] = None
        self.last_ts: Optional[float] = None
        self._resolved = False
        self.updated = Event()
        gateway.events.connect(self._on_event)
        catalog.loaded.connect(self._resolve_saved)
        state.disconnected.connect(lambda *_: self._mark_stopped())

    def reload(self) -> None:
        self._stop_sources()
        self.saved_names, rate = read_data_logger(self._store.load())
        self.rate_s = clamp_rate(rate)
        self.series = []
        self._resolved = False
        self._resolve_saved()
        self.updated.emit()

    # ---- state ---------------------------------------------------------------------------------

    @property
    def recording(self) -> bool:
        return self._sub.active or self._poll is not None

    @property
    def mode(self) -> str:
        return "watch" if uses_watch(self.rate_s) else "polling"

    @property
    def elapsed_s(self) -> float:
        return (self.last_ts - self.t0) if self.t0 is not None and self.last_ts is not None else 0.0

    # ---- fields ----------------------------------------------------------------------------------

    def _resolve_saved(self) -> None:
        if not self._catalog.peripherals:
            return  # catalog cleared on disconnect: keep the list as it is
        names = [s.name for s in self.series] if self._resolved else self.saved_names
        self._resolved = True
        self.series = []
        for name in names:
            self._add(name)
        self.updated.emit()

    def _add(self, full_name: str) -> bool:
        if any(s.name == full_name for s in self.series):
            return False
        reg, fdef = self._catalog.resolve(full_name)
        if reg is None:
            return False
        entry = self._annotations.formula(full_name)
        self.series.append(Series(full_name, reg, fdef, unit=entry[1] if entry else ""))
        return True

    def track(self, full_name: str) -> bool:
        added = self._add(full_name)
        if added:
            self._save()
            if self.recording:
                self.start()
        return added

    def untrack(self, full_name: str) -> None:
        self.series = [s for s in self.series if s.name != full_name]
        self._save()
        if self.recording:
            self.start() if self.series else self.stop()

    # ---- recording -------------------------------------------------------------------------------

    def set_rate(self, rate_s: float) -> None:
        self.rate_s = clamp_rate(rate_s)
        self._save()
        if self.recording:
            self.start()

    def start(self, rate_s: Optional[float] = None) -> Call:
        if rate_s is not None:
            self.rate_s = clamp_rate(rate_s)
            self._save()
        self._stop_sources()
        names = self._register_names()
        if uses_watch(self.rate_s):
            call = self._sub.start(names, self.rate_s, "Data logger")
        else:
            self._poll = self._scheduler.every(max(1, round(self.rate_s * 1000)), self._poll_once)
            call = Call.succeeded(None)
        call.then(lambda _: self.updated.emit())
        return call

    def stop(self) -> None:
        self._stop_sources()
        self.updated.emit()

    def clear(self) -> None:
        for s in self.series:
            s.samples.clear()
            s.times.clear()
            s.values.clear()
        self.sample_count = 0
        self.t0 = self.last_ts = None
        self.updated.emit()

    def _stop_sources(self) -> None:
        self._sub.stop()
        if self._poll is not None:
            self._poll.cancel()
            self._poll = None

    def _mark_stopped(self) -> None:
        self._sub.forget()
        if self._poll is not None:
            self._poll.cancel()
            self._poll = None
        self.updated.emit()

    def _register_names(self) -> List[str]:
        return sorted({s.register.full_name for s in self.series})

    def _poll_once(self) -> None:
        def apply(items: List[ReadManyItem]) -> None:
            self._record({i.name: i.value for i in items if i.value is not None}, self._clock())

        def failed(error: ApiError) -> None:
            self.stop()  # one message, not one per tick
            self._errors.present(error, "Data logger")

        self._gateway.read_many(self._state.position, self._register_names()).then(apply, failed)

    def _on_event(self, event: object) -> None:
        if isinstance(event, WatchValues) and event.sub_id == self._sub.sub_id:
            self._record(event.values, event.ts)

    def _record(self, values: Dict[str, int], ts: float) -> None:
        if not values:
            return
        if self.t0 is None:
            self.t0 = ts
        self.last_ts = ts
        sample = self.sample_count
        for s in self.series:
            if s.register.full_name not in values:
                continue
            raw = s.field.extract(values[s.register.full_name]) if s.field else values[s.register.full_name]
            calc = self._annotations.calculate(s.name, raw)
            s.samples.append(sample)
            s.times.append(ts - self.t0)
            s.values.append(calc if calc is not None else float(raw))
            if len(s.values) > MAX_POINTS:
                del s.samples[0], s.times[0], s.values[0]
        self.sample_count += 1
        self.updated.emit()

    # ---- files -----------------------------------------------------------------------------------

    def export_csv(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["field", "sample", "t_s", "value", "unit"])
            for s in self.series:
                for n, t, v in zip(s.samples, s.times, s.values):
                    writer.writerow([s.name, n, f"{t:.3f}", v, s.unit])
        return path

    def _save(self) -> None:
        # before the catalog loads, the saved names can't be resolved yet, so keep them as they are
        names = [s.name for s in self.series] if self._resolved else self.saved_names
        self.saved_names = names
        self._store.save(write_data_logger(names, self.rate_s))
        self.updated.emit()
