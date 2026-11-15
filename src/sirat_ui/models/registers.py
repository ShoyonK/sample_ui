"""Register map types: access, enum values, fields, registers, peripherals, the chip, search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from sirat_ui.core import bits


class AccessType(str, Enum):
    """A register's or field's access, from the SVD."""
    READ_ONLY = "ro"
    WRITE_ONLY = "wo"
    READ_WRITE = "rw"
    WRITE_ONCE = "w1"
    READ_WRITE_ONCE = "rw1"
    UNKNOWN = "unknown"

    @classmethod
    def from_svd(cls, text: str) -> "AccessType":
        """The access type for an SVD access string ("read-write", "rw", ...); UNKNOWN for anything else."""
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
    AccessType.READ_ONLY: "Read",
    AccessType.READ_WRITE: "Read/Write",
    AccessType.WRITE_ONLY: "Write",
    AccessType.WRITE_ONCE: "Write once",
    AccessType.READ_WRITE_ONCE: "Read/Write once",
    AccessType.UNKNOWN: "Unknown",
}


@dataclass(frozen=True)
class EnumValue:
    """A named value of a field."""
    name: str
    value: int
    description: str = ""


@dataclass(frozen=True)
class FieldDef:
    """A register field: bits [lsb, lsb + width) of `register` (the register's full name)."""
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
        return next((enum for enum in self.enums if enum.value == value), None)


@dataclass(frozen=True)
class RegisterDef:
    """A register. critical: writes need confirmation (CMU, EMU). read_sensitive: reading has side effects
    (clears a FIFO or flags), so bulk reads and watches skip it."""
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
        return next((f for f in self.fields if f.name == name), None)


@dataclass(frozen=True)
class PeripheralDef:
    """A peripheral and its registers."""
    name: str
    base_address: int
    description: str = ""
    registers: Tuple[RegisterDef, ...] = field(default_factory=tuple)

    @property
    def is_secure_variant(self) -> bool:
        return self.name.endswith(("_NS", "_S"))


@dataclass(frozen=True)
class ChipInfo:
    """The connected chip: part, revision, family."""
    part: str
    revision: str
    family: str

    @property
    def label(self) -> str:
        return f"{self.part} · rev{self.revision}"

    @property
    def short(self) -> str:
        return f"{self.family} {self.revision}"


@dataclass
class SearchResult:
    """The tree filter's result (core/search.py): the peripherals to show, which of their registers, which are
    expanded by the search, and a register to select when exactly one matched."""
    peripherals: List[str] = field(default_factory=list)
    # None means "show every register of this peripheral"
    registers: Dict[str, Optional[List[str]]] = field(default_factory=dict)
    expanded: Set[str] = field(default_factory=set)
    auto_select: Optional[str] = None
    is_empty_query: bool = True
