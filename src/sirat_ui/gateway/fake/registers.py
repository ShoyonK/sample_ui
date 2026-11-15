"""registers.* for the fake station: the tree, reads, checked writes and watch subscriptions.

FakeRegisters does the work and owns the watch subscriptions; it reads the chip, the register values and the
positions from its host (the station, through RegistersHost), like FakeAdvanced does. RegisterMethods is the mixin
that gives FakeStationGateway the registers.* methods by handing each call to its FakeRegisters.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol

from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.fake.register_memory import RegisterMemory
from sirat_ui.gateway.scheduler import Handle, Scheduler
from sirat_ui.models.facts import PositionFacts
from sirat_ui.models.registers import PeripheralDef
from sirat_ui.models.station import ReadManyItem, WatchValues, WriteResult

Respond = Callable[..., Call]


@dataclass
class Watch:
    """One registers.watch subscription."""
    sub_id: str
    position: int
    names: List[str]
    interval_s: float
    handle: Handle


class RegistersHost(Protocol):
    """What FakeRegisters needs from the station: the chip, its register values, the positions, and the
    drop_after_reads knob (the DUT drops on that read, then the knob clears)."""
    peripherals: List[PeripheralDef]
    memory: RegisterMemory
    facts: Dict[int, PositionFacts]
    drop_after_reads: Optional[int]

    def drop_dut(self, position: int, cause: str = ..., detected_by: str = ...) -> None: ...


class FakeRegisters:
    """registers.* behind the fake station. `reads` counts registers.read calls, for drop_after_reads."""

    def __init__(self, respond: Respond, emit_event: Callable[[Any], None], host: RegistersHost,
                 scheduler: Scheduler, clock: Callable[[], float]) -> None:
        self._respond = respond
        self._emit_event = emit_event
        self._host = host
        self._scheduler = scheduler
        self._clock = clock
        self._ids = itertools.count(1)
        self.watches: Dict[str, Watch] = {}
        self.reads = 0

    def register_tree(self, position: int) -> Call[List[PeripheralDef]]:
        return self._respond("registers.tree", position, lambda: list(self._host.peripherals))

    def read_register(self, position: int, name: str) -> Call[int]:
        def run() -> int:
            self.reads += 1
            host = self._host
            if host.drop_after_reads is not None and self.reads >= host.drop_after_reads:
                host.drop_after_reads = None
                host.drop_dut(position, "RPC connection lost", "registers.read")
                raise ApiError(ErrorCode.DUT_DISCONNECTED, f"Disconnected - Cannot read register {name}")
            return host.memory.read(name)
        return self._respond("registers.read", position, run, name=name)

    def read_many(self, position: int, names: List[str],
                  include_read_sensitive: bool = False) -> Call[List[ReadManyItem]]:
        memory = self._host.memory

        def run() -> List[ReadManyItem]:
            items = []
            for name in names:
                reg = memory.lookup(name)
                if reg is not None and reg.read_sensitive and not include_read_sensitive:
                    error = ApiError(ErrorCode.READ_SENSITIVE, f"{name} is read-sensitive")
                    items.append(ReadManyItem(name, error=error))
                    continue
                try:
                    items.append(ReadManyItem(name, value=memory.read(name)))
                except ApiError as exc:
                    items.append(ReadManyItem(name, error=exc))
            return items
        return self._respond("registers.read_many", position, run, names=list(names),
                             include_read_sensitive=include_read_sensitive)

    def _checked_write(self, name: str, new_value: int, confirm: bool, verify: bool,
                       expect: Callable[[int], int], wanted: int) -> WriteResult:
        memory = self._host.memory
        reg = memory.get(name)
        if reg.critical and not confirm:
            raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, f"{name} is in a critical peripheral", {"register": name})
        readback = memory.write(name, new_value)
        if not reg.access.readable:
            return WriteResult(new_value, None, True)    # nothing to read back
        verified = not (verify and expect(readback) != wanted)
        return WriteResult(new_value, readback, verified)

    def write_register(self, position: int, name: str, value: int, confirm: bool = False,
                       verify: bool = True) -> Call[WriteResult]:
        return self._respond("registers.write", position,
                             lambda: self._checked_write(name, value, confirm, verify, lambda rb: rb, value),
                             name=name, value=value, confirm=confirm)

    def write_field(self, position: int, name: str, field: str, value: int,
                    confirm: bool = False, verify: bool = True) -> Call[WriteResult]:
        memory = self._host.memory

        def run() -> WriteResult:
            new_value = memory.field_insert(name, field, value)
            fdef = memory.get(name).field(field)
            assert fdef is not None  # field_insert raised NOT_FOUND otherwise
            return self._checked_write(name, new_value, confirm, verify, fdef.extract, value)
        return self._respond("registers.write_field", position, run, name=name, field=field, value=value,
                             confirm=confirm)

    def watch(self, position: int, names: List[str], interval_s: float,
              include_read_sensitive: bool = False) -> Call[str]:
        def run() -> str:
            if not 0.1 <= interval_s <= 60:
                raise ApiError(ErrorCode.INVALID_PARAMS, "interval_s must be between 0.1 and 60")
            for name in names:
                reg = self._host.memory.get(name)
                if reg.read_sensitive and not include_read_sensitive:
                    raise ApiError(ErrorCode.READ_SENSITIVE, f"{name} is read-sensitive", {"register": name})
            sub_id = f"w{next(self._ids)}"
            handle = self._scheduler.every(int(interval_s * 1000), lambda: self.tick(sub_id))
            self.watches[sub_id] = Watch(sub_id, position, list(names), interval_s, handle)
            self._host.facts[position].watching = True
            return sub_id
        return self._respond("registers.watch", position, run, names=list(names), interval_s=interval_s)

    def unwatch(self, sub_id: str) -> Call[None]:
        def run() -> None:
            watch = self.watches.pop(sub_id, None)
            if watch:
                watch.handle.cancel()
                still = any(w.position == watch.position for w in self.watches.values())
                self._host.facts[watch.position].watching = still
        return self._respond("registers.unwatch", None, run, sub_id=sub_id)

    def tick(self, sub_id: str) -> None:
        """One watch update: the live registers move on and the subscription's values are pushed."""
        watch = self.watches.get(sub_id)
        if watch is None or not self._host.facts[watch.position].dut_connected:
            return
        memory = self._host.memory
        memory.advance_live()
        values = {name: memory.values[name] for name in watch.names}
        self._emit_event(WatchValues(sub_id, watch.position, self._clock(), values))

    def drop_watches(self, position: int) -> None:
        """Ends the position's subscriptions (a disconnect clears them)."""
        for sub_id in [s for s, w in self.watches.items() if w.position == position]:
            self.watches.pop(sub_id).handle.cancel()


class RegisterMethods:
    """FakeStationGateway's registers.* methods; the work is in its FakeRegisters."""
    fake_registers: FakeRegisters

    def register_tree(self, position: int) -> Call[List[PeripheralDef]]:
        return self.fake_registers.register_tree(position)

    def read_register(self, position: int, name: str) -> Call[int]:
        return self.fake_registers.read_register(position, name)

    def read_many(self, position: int, names: List[str],
                  include_read_sensitive: bool = False) -> Call[List[ReadManyItem]]:
        return self.fake_registers.read_many(position, names, include_read_sensitive)

    def write_register(self, position: int, name: str, value: int, confirm: bool = False,
                       verify: bool = True) -> Call[WriteResult]:
        return self.fake_registers.write_register(position, name, value, confirm, verify)

    def write_field(self, position: int, name: str, field: str, value: int,
                    confirm: bool = False, verify: bool = True) -> Call[WriteResult]:
        return self.fake_registers.write_field(position, name, field, value, confirm, verify)

    def watch(self, position: int, names: List[str], interval_s: float,
              include_read_sensitive: bool = False) -> Call[str]:
        return self.fake_registers.watch(position, names, interval_s, include_read_sensitive)

    def unwatch(self, sub_id: str) -> Call[None]:
        return self.fake_registers.unwatch(sub_id)
