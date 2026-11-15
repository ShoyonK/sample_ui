"""registers: the register tree, reads, writes and watches; and the registers.watch event."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pydantic import Field
from typing_extensions import Annotated, TypedDict

from station_protocol.common import POS
from station_protocol.errors import ApiError
from station_protocol.method import Event, Method, Param

WatchInterval = Annotated[float, Field(ge=0.1, le=60)]


class AccessType(str, Enum):
    """A register's or field's access, from the SVD."""
    READ_ONLY = "ro"
    WRITE_ONLY = "wo"
    READ_WRITE = "rw"
    WRITE_ONCE = "w1"
    READ_WRITE_ONCE = "rw1"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EnumValue:
    """A named value of a field."""
    name: str
    value: int
    description: str = ""


class FieldInfo(TypedDict):
    name: str
    lsb: int
    width: int
    access: AccessType
    description: str
    enums: List[EnumValue]


class RegisterInfo(TypedDict):
    name: str
    address: int
    width: int
    access: AccessType
    reset_value: Optional[int]
    description: str
    fields: List[FieldInfo]


class PeripheralInfo(TypedDict):
    name: str
    base_address: int
    description: str
    critical: bool            # writes need confirm=true (CMU, EMU, MSC, SMU)
    read_sensitive: bool      # reading has side effects (USART, I2C, SPI)
    registers: List[RegisterInfo]


class RegisterTree(TypedDict):
    tree_id: str              # content hash; a client caches by (chip, revision, tree_id)
    peripherals: List[PeripheralInfo]


@dataclass
class WriteResult:
    """registers.write / write_field (API WriteRes). value_written is the whole register value written."""
    value_written: int
    value_readback: Optional[int]   # None when the register can't be read back (write-only)
    verified: bool = True           # False: the read-back differs. The write happened; the client warns (req 7)


@dataclass
class ReadManyItem:
    """One register of registers.read_many: a value or an error."""
    name: str
    value: Optional[int] = None
    error: Optional[ApiError] = None


class WatchValue(TypedDict):
    name: str
    value: int


class WatchData(TypedDict):
    sub_id: str
    pos: int
    ts: float                  # unix seconds
    values: List[WatchValue]


DUT = ("dut",)
WRITE = ("dut", "idle")

METHODS = (
    Method("registers.tree", (POS,), RegisterTree, requires=DUT),
    Method("registers.read", (POS, Param("name", str)), int, wrap="value", requires=DUT),
    Method("registers.read_many", (POS, Param("names", List[str]), Param("include_read_sensitive", bool, False)),
           List[ReadManyItem], wrap="items", requires=DUT),
    Method("registers.write", (POS, Param("name", str), Param("value", int), Param("confirm", bool, False),
                               Param("verify", bool, True)), WriteResult, requires=WRITE),
    Method("registers.write_field", (POS, Param("name", str), Param("field", str), Param("value", int),
                                     Param("confirm", bool, False), Param("verify", bool, True)), WriteResult,
           requires=WRITE),
    Method("registers.watch", (POS, Param("names", List[str]), Param("interval_s", WatchInterval),
                               Param("include_read_sensitive", bool, False)), str, wrap="sub_id", requires=DUT),
    Method("registers.unwatch", (Param("sub_id", str),), None),
)

WATCH = Event("registers.watch", WatchData, "watch")
