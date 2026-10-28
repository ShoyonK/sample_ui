"""Frontend register models. Wire models from the Station API are mapped into these by the gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from sirat_ui.core import bits


class AccessType(str, Enum):
    READ_ONLY = "ro"
    WRITE_ONLY = "wo"
    READ_WRITE = "rw"
    WRITE_ONCE = "w1"
    READ_WRITE_ONCE = "rw1"
    UNKNOWN = "unknown"

    @classmethod
    def from_svd(cls, text: str) -> "AccessType":
        return _SVD_ACCESS.get((text or "").strip(), cls.UNKNOWN)

    @property
    def label(self) -> str:
        return _ACCESS_LABELS[self]

    @property
    def readable(self) -> bool:
        return self in (AccessType.READ_ONLY, AccessType.READ_WRITE, AccessType.READ_WRITE_ONCE)

    @property
    def writable(self) -> bool:
        return self in (AccessType.WRITE_ONLY, AccessType.READ_WRITE, AccessType.WRITE_ONCE, AccessType.READ_WRITE_ONCE)


_SVD_ACCESS = {
    "read-only": AccessType.READ_ONLY,
    "ro": AccessType.READ_ONLY,
    "write-only": AccessType.WRITE_ONLY,
    "wo": AccessType.WRITE_ONLY,
    "read-write": AccessType.READ_WRITE,
    "rw": AccessType.READ_WRITE,
    "writeOnce": AccessType.WRITE_ONCE,
    "read-writeOnce": AccessType.READ_WRITE_ONCE,
}

_ACCESS_LABELS = {
    AccessType.READ_ONLY: "R",
    AccessType.READ_WRITE: "RW",
    AccessType.WRITE_ONLY: "W",
    AccessType.WRITE_ONCE: "W1",
    AccessType.READ_WRITE_ONCE: "RW1",
    AccessType.UNKNOWN: "?",
}


@dataclass(frozen=True)
class EnumValue:
    name: str
    value: int
    description: str = ""


@dataclass(frozen=True)
class FieldDef:
    register: str
    name: str
    lsb: int
    width: int
    access: AccessType = AccessType.READ_WRITE
    description: str = ""
    enums: Tuple[EnumValue, ...] = ()

    @property
    def full_name(self) -> str:
        return f"{self.register}.{self.name}"

    @property
    def msb(self) -> int:
        return self.lsb + self.width - 1

    @property
    def bits_text(self) -> str:
        return str(self.lsb) if self.width == 1 else f"{self.msb}-{self.lsb}"

    @property
    def max_value(self) -> int:
        return bits.mask(self.width)

    @property
    def mask(self) -> int:
        return bits.mask(self.width) << self.lsb

    def extract(self, register_value: int) -> int:
        return bits.extract(register_value, self.lsb, self.width)

    def insert(self, register_value: int, value: int) -> int:
        return bits.insert(register_value, self.lsb, self.width, value)

    def enum_for(self, value: int) -> Optional[EnumValue]:
        for enum in self.enums:
            if enum.value == value:
                return enum
        return None


@dataclass(frozen=True)
class RegisterDef:
    peripheral: str
    name: str
    address: int
    access: AccessType = AccessType.READ_WRITE
    width: int = 32
    description: str = ""
    fields: Tuple[FieldDef, ...] = ()
    reset: int = 0
    critical: bool = False
    read_sensitive: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.peripheral}.{self.name}"

    @property
    def max_value(self) -> int:
        return bits.mask(self.width)

    @property
    def writable_mask(self) -> int:
        """Bits a write can change. Registers without fields are fully writable."""
        if not self.fields:
            return self.max_value
        value = 0
        for f in self.fields:
            if f.access.writable:
                value |= f.mask
        return value

    def field(self, name: str) -> Optional[FieldDef]:
        for f in self.fields:
            if f.name == name:
                return f
        return None


@dataclass(frozen=True)
class PeripheralDef:
    name: str
    base_address: int
    description: str = ""
    registers: Tuple[RegisterDef, ...] = field(default_factory=tuple)

    @property
    def is_secure_variant(self) -> bool:
        return self.name.endswith("_NS") or self.name.endswith("_S")


@dataclass(frozen=True)
class ChipInfo:
    part: str
    revision: str
    family: str

    @property
    def label(self) -> str:
        return f"{self.part} · rev{self.revision}"

    @property
    def short(self) -> str:
        return f"{self.family} {self.revision}"
