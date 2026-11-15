"""Watch list (req 18): live values over a registers.watch subscription, persisted in the original format."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from sibench_ui.core.observable import Event
from sibench_ui.domains.monitoring.saved_list import SavedList
from sibench_ui.domains.monitoring.subscription import WATCH_MAX_S, WATCH_MIN_S, WatchSubscription
from sibench_ui.domains.registers.catalog import RegisterCatalog
from sibench_ui.domains.registers.service import RegisterService
from sibench_ui.gateway.call import Call
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.port import RegistersPort
from sibench_ui.models.registers import FieldDef, RegisterDef
from sibench_ui.models.station import ReadManyItem, WatchValues
from sibench_ui.shared.error_presenter import ErrorPresenter
from sibench_ui.state.station import StationState
from sibench_ui.stores.formats import read_watch_list, write_watch_list
from sibench_ui.stores.json_store import JsonStore

TREND_POINTS = 20


def clamp_interval(interval_s: float) -> float:
    """An interval registers.watch accepts."""
    return max(WATCH_MIN_S, min(WATCH_MAX_S, interval_s))


@dataclass
class WatchItem:
    """One watched register or field: its latest value, whether the last update changed it, and a short trend."""
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
    """The watch list (see the module docstring)."""

    def __init__(self, gateway: RegistersPort, state: StationState, catalog: RegisterCatalog,
                 registers: RegisterService, store: JsonStore, errors: ErrorPresenter,
                 clock: Callable[[], float] = time.time) -> None:
        self._gateway = gateway
        self._state = state
        self._registers = registers
        self._store = store
        self._clock = clock
        self._sub = WatchSubscription(gateway, state, errors)
        self._errors = errors
        names, interval = read_watch_list(store.load())
        self.interval_s = clamp_interval(interval)
        self._list: SavedList[WatchItem] = SavedList(catalog, names, self._make_item)
        self.updated = Event()
        gateway.events.connect(self._on_event)
        catalog.loaded.connect(self._resolve_saved)
        registers.value_changed.connect(self._on_register_value)
        state.disconnected.connect(lambda *_: self._mark_stopped())

    def reload(self) -> None:
        self.stop()
        names, interval = read_watch_list(self._store.load())
        self.interval_s = clamp_interval(interval)
        self._list.reset(names)
        self._resolve_saved()
        self.updated.emit()

    @property
    def items(self) -> List[WatchItem]:
        return self._list.items

    @property
    def saved_names(self) -> List[str]:
        return self._list.names

    @property
    def live(self) -> bool:
        return self._sub.active

    def _resolve_saved(self) -> None:
        if self._list.resolve():
            self.updated.emit()

    def _make_item(self, full_name: str, reg: RegisterDef, fdef: Optional[FieldDef]) -> WatchItem:
        """A new row, showing the register's last read value when there is one."""
        cached = self._registers.cached(reg.full_name)
        seed = None if cached is None else (fdef.extract(cached) if fdef else cached)
        return WatchItem(full_name, reg, fdef, seed)

    def add(self, full_name: str) -> bool:
        added = self._list.add(full_name)
        if added:
            self._save()
            if self.live:
                self.start(self.interval_s)
        return added

    def remove(self, full_name: str) -> None:
        self._list.remove(full_name)
        self._save()
        if self.live:
            self.start(self.interval_s) if self.items else self.stop()

    def clear(self) -> None:
        self._list.clear()
        self.stop()
        self._save()

    def set_interval(self, interval_s: float) -> None:
        self.interval_s = clamp_interval(interval_s)
        self._save()
        if self.live:
            self.start()

    def start(self, interval_s: Optional[float] = None) -> Call[str]:
        if interval_s is not None:
            self.interval_s = clamp_interval(interval_s)
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
        """Writes a watched register or field (through RegisterService, so it's confirmed and recorded)."""
        item = self._list.get(full_name)
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
        self._store.save(write_watch_list(self._list.names, self.interval_s))
        self.updated.emit()
