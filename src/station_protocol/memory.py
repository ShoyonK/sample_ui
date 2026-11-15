"""memory: reading and writing the DUT's memory by address."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field
from typing_extensions import Annotated, Literal

from station_protocol.common import POS
from station_protocol.method import Method, Param

ReadSize = Annotated[int, Field(ge=1, le=4096)]
WriteSize = Literal[1, 2, 4]


@dataclass(frozen=True)
class MemoryBlock:
    """memory.read: `address` is the aligned start actually read; data is base64."""
    address: int
    data: str


@dataclass(frozen=True)
class MemoryWriteRes:
    """memory.write: what was written and read back."""
    address: int
    value_written: int
    value_readback: int


METHODS = (
    Method("memory.read", (POS, Param("address", int), Param("size", ReadSize)), MemoryBlock, requires=("dut",)),
    Method("memory.write", (POS, Param("address", int), Param("value", int), Param("size", WriteSize)),
           MemoryWriteRes, requires=("dut", "idle")),
)
