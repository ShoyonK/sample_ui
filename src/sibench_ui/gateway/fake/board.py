"""FakeBoard: the DUT at one position of the fake station, with its own chip, registers and address space.

Each position has its own board, so a write on DUT 1 never shows on DUT 2, and two positions can hold different
chips with different register trees (FakeStationGateway.replace_dut).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sibench_ui.gateway.fake.memory import FakeMemory
from sibench_ui.gateway.fake.register_memory import RegisterMemory
from sibench_ui.models.registers import ChipInfo, PeripheralDef


@dataclass
class FakeBoard:
    """One DUT: what chip it is, its register tree and values, and its memory (RAM, flash, peripherals)."""
    chip: ChipInfo
    peripherals: List[PeripheralDef]
    memory: RegisterMemory
    ram: FakeMemory

    @classmethod
    def build(cls, chip: ChipInfo, peripherals: List[PeripheralDef], seed: int) -> "FakeBoard":
        """A board at reset: every register at its reset value."""
        memory = RegisterMemory(peripherals, seed)
        return cls(chip, peripherals, memory, FakeMemory(peripherals, memory, seed))
