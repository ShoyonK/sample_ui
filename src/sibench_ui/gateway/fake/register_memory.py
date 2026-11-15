"""Register values for the fake chip, with write masks and a few "live" registers that drift."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.models.registers import PeripheralDef, RegisterDef

_RAC_STATES = (1, 3, 3, 4, 3)                 # RXWARM, RXSEARCH, RXSEARCH, RXFRAME, RXSEARCH
_DEMOD_STATE = {1: 1, 3: 2, 4: 5}             # RAC state -> MODEM.STATUS DEMODSTATE (warming, searching, frame)
_RXFRAME = 4


class RegisterMemory:
    """The fake chip's register values, starting at reset values; writes go through each register's writable mask."""

    def __init__(self, peripherals: List[PeripheralDef], seed: int = 7) -> None:
        self.registers: Dict[str, RegisterDef] = {r.full_name: r for p in peripherals for r in p.registers}
        self.values: Dict[str, int] = {name: reg.reset for name, reg in self.registers.items()}
        self._rng = random.Random(seed)
        self._tick = 0

    def get(self, name: str) -> RegisterDef:
        reg = self.registers.get(name)
        if reg is None:
            raise ApiError(ErrorCode.NOT_FOUND, f"Register {name} doesn't exist")
        return reg

    def read(self, name: str) -> int:
        """The register's value. Raises ApiError NOT_FOUND / ACCESS_DENIED (write-only)."""
        reg = self.get(name)
        if not reg.access.readable:
            raise ApiError(ErrorCode.ACCESS_DENIED, f"{name} is write-only")
        return self.values[name]

    def write(self, name: str, value: int) -> int:
        """Applies a write through the writable mask and returns the read-back value."""
        reg = self.get(name)
        if not reg.access.writable:
            raise ApiError(ErrorCode.ACCESS_DENIED, f"{name} is read-only")
        if value < 0 or value > reg.max_value:
            raise ApiError(ErrorCode.OUT_OF_RANGE, f"0x{value:X} doesn't fit in {name}", {"max": reg.max_value})
        mask = reg.writable_mask
        new_value = (self.values[name] & ~mask) | (value & mask)
        self.values[name] = new_value
        return new_value if reg.access.readable else value

    def field_insert(self, name: str, field_name: str, value: int) -> int:
        """The whole register value with one field replaced; doesn't write it. Raises ApiError when invalid."""
        reg = self.get(name)
        field = reg.field(field_name)
        if field is None:
            raise ApiError(ErrorCode.NOT_FOUND, f"Field {name}.{field_name} doesn't exist")
        if not field.access.writable:
            raise ApiError(ErrorCode.ACCESS_DENIED, f"{field.full_name} is read-only")
        if value < 0 or value > field.max_value:
            raise ApiError(ErrorCode.OUT_OF_RANGE, f"0x{value:X} is out of range for {field.full_name}",
                           {"max": field.max_value})
        return field.insert(self.values[name], value)

    def advance_live(self) -> None:
        """Makes a few registers change between watch ticks, like real radio state would."""
        self._tick += 1
        self._set_if_present("SYNTH.FREQ", 2_440_000 + self._rng.randint(-3, 3))
        self._set_if_present("AGC.RSSI", (self._rng.randint(-86, -68)) & 0xFFFF)
        state = _RAC_STATES[self._tick % len(_RAC_STATES)]
        self._set_if_present("RAC.STATUS", state)
        self._set_if_present("MODEM.STATUS", _DEMOD_STATE[state])
        self._set_if_present("FRC.STATUS", int(state == _RXFRAME))
        waiting = self._rng.randint(0, 64)
        self._set_if_present("BUFC.BUF0_STATUS", waiting)
        if "BUFC.BUF0_WRITEOFFSET" in self.values:   # frames arrive: the write offset moves on, reads trail it
            written = (self.values["BUFC.BUF0_WRITEOFFSET"] + 24 + waiting) & 0x1FFF
            self._set_if_present("BUFC.BUF0_WRITEOFFSET", written)
            self._set_if_present("BUFC.BUF0_READOFFSET", (written - waiting) & 0x1FFF)

    def _set_if_present(self, name: str, value: int) -> None:
        if name in self.values:
            self.values[name] = value

    def lookup(self, name: str) -> Optional[RegisterDef]:
        return self.registers.get(name)
