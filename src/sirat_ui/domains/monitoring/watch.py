"""Watch list (req 18): live values over a registers.watch subscription, persisted in the original format."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.domains.monitoring.subscription import WATCH_MAX_S, WATCH_MIN_S, WatchSubscription
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.port import RegistersPort
from sirat_ui.models.registers import FieldDef, RegisterDef
from sirat_ui.models.station import ReadManyItem, WatchValues
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState
from sirat_ui.stores.formats import read_watch_list, write_watch_list
from sirat_ui.stores.json_store import JsonStore

TREND_POINTS = 20


@dataclass
class WatchItem:
    name: str
    register: RegisterDef
    field: Optional[FieldDef]
    value: Optional[int] = None
    changed: bool = False
    changed_at: Optional[float] = None
    trend: List[int] = field(default_factory=list)

    def raw(self, register_value: int) -> int:
        return self.field.extract(register_value) if self.field else register_value


class WatchService:
    def __init__(self, gateway: RegistersPort, state: StationState, catalog: RegisterCatalog,
                 registers: RegisterService, store: JsonStore, errors: ErrorPresenter,
                 clock: Callable[[], float] = time.time) -> None:
        self._gateway = gateway
        self._state = state
        self._catalog = catalog
        self._registers = registers
        self._store = store
        self._clock = clock
        self._sub = WatchSubscription(gateway, state, errors)
        self._errors = errors
        self.saved_names, self.interval_s = read_watch_list(store.load())
        self.interval_s = max(WATCH_MIN_S, min(WATCH_MAX_S, self.interval_s))
        self.items: List[WatchItem] = []
        self._resolved = False
        self.updated = Event()
        gateway.events.connect(self._on_event)
        catalog.loaded.connect(self._resolve_saved)
        registers.value_changed.connect(self._on_register_value)
        state.disconnected.connect(lambda *_: self._mark_stopped())

    def reload(self) -> None:
        self.stop()
        self.saved_names, interval = read_watch_list(self._store.load())
        self.interval_s = max(WATCH_MIN_S, min(WATCH_MAX_S, interval))
        self.items = []
        self._resolved = False
        self._resolve_saved()
        self.updated.emit()

    @property
    def live(self) -> bool:
        return self._sub.active

    def _resolve_saved(self) -> None:
        if not self._catalog.peripherals:
            return  # catalog cleared on disconnect: keep the list as it is
        names = [i.name for i in self.items] if self._resolved else self.saved_names
        self._resolved = True
        self.items = []
        for name in names:
            self._add_item(name)
        self.updated.emit()

    def _add_item(self, full_name: str) -> bool:
        if any(i.name == full_name for i in self.items):
            return False
        reg, fdef = self._catalog.resolve(full_name)
        if reg is None:
            return False
        self.items.append(WatchItem(full_name, reg, fdef, self._seed(reg, fdef)))
        return True

    def _seed(self, reg: RegisterDef, fdef: Optional[FieldDef]) -> Optional[int]:
        cached = self._registers.cached(reg.full_name)
        if cached is None:
            return None
        return fdef.extract(cached) if fdef else cached

    def add(self, full_name: str) -> bool:
        added = self._add_item(full_name)
        if added:
            self._save()
            if self.live:
                self.start(self.interval_s)
        return added

    def remove(self, full_name: str) -> None:
        self.items = [i for i in self.items if i.name != full_name]
        self._save()
        if self.live:
            self.start(self.interval_s) if self.items else self.stop()

    def clear(self) -> None:
        self.items = []
        self.stop()
        self._save()

    def set_interval(self, interval_s: float) -> None:
        self.interval_s = max(WATCH_MIN_S, min(WATCH_MAX_S, interval_s))
        self._save()
        if self.live:
            self.start()

    def start(self, interval_s: Optional[float] = None) -> Call:
        if interval_s is not None:
            self.interval_s = max(WATCH_MIN_S, min(WATCH_MAX_S, interval_s))
        names = sorted({i.register.full_name for i in self.items})
        call = self._sub.start(names, self.interval_s, "Watch list")
        call.then(lambda _: self.updated.emit())
        return call

    def stop(self) -> None:
        self._sub.stop()
        self.updated.emit()

    def _mark_stopped(self) -> None:
        self._sub.forget()
        self.updated.emit()

    def refresh_once(self) -> Call:
        names = sorted({i.register.full_name for i in self.items})

        def apply(items: List[ReadManyItem]) -> None:
            now = self._clock()
            for item in items:
                if item.value is not None:
                    self._apply(item.name, item.value, now)
            self.updated.emit()

        return self._gateway.read_many(self._state.position, names).then(
            apply, lambda e: self._errors.present(e, "Refresh watch list"))

    def write(self, full_name: str, value: int) -> Call:
        item = next((i for i in self.items if i.name == full_name), None)
        if item is None:
            return Call.failed(ApiError(ErrorCode.NOT_FOUND, f"{full_name} isn't in the watch list"))
        if item.field:
            return self._registers.write_field(item.register, item.field, value)
        return self._registers.write(item.register, value)

    def _on_event(self, event: object) -> None:
        if isinstance(event, WatchValues) and event.sub_id == self._sub.sub_id:
            for item in self.items:
                item.changed = False
            for name, value in event.values.items():
                self._apply(name, value, event.ts)
            self.updated.emit()

    def _on_register_value(self, full_name: str, value: Optional[int]) -> None:
        if value is not None and any(i.register.full_name == full_name for i in self.items):
            self._apply(full_name, value, self._clock())
            self.updated.emit()

    def _apply(self, register_name: str, register_value: int, ts: float) -> None:
        for item in self.items:
            if item.register.full_name != register_name:
                continue
            raw = item.raw(register_value)
            item.changed = item.value is not None and raw != item.value
            if item.changed:
                item.changed_at = ts
            item.value = raw
            item.trend = (item.trend + [raw])[-TREND_POINTS:]

    def _save(self) -> None:
        # before the catalog loads, the saved names can't be resolved yet, so keep them as they are
        names = [i.name for i in self.items] if self._resolved else self.saved_names
        self.saved_names = names
        self._store.save(write_watch_list(names, self.interval_s))
        self.updated.emit()
