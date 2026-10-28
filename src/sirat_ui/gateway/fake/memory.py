"""Raw memory for the fake chip (req 19): flash, RAM and the peripheral window, like an EFR32 series 2 map.

Flash is read-only, RAM is read-write, and the peripheral window reads and writes the fake registers at their
addresses, so the memory viewer and the register pages agree. A RAM word at 0x20000100 counts reads, so
consecutive reads show something changing.
"""

from __future__ import annotations

import random
import struct
from typing import Dict, List, Optional, Tuple

from sirat_ui.core.memory import crosses_word
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.fake.register_memory import RegisterMemory
from sirat_ui.models.registers import PeripheralDef

PAGE = 4096
FLASH = (0x0800_0000, 0x10_0000)     # 1 MB
RAM = (0x2000_0000, 0x4_0000)        # 256 KB
PERIPHERALS = (0x4000_0000, 0x8000_0000)   # radio blocks sit up to 0xBFFFFFFF
READ_COUNTER = 0x2000_0100
MAP_TEXT = ("flash 0x08000000–0x080FFFFF, RAM 0x20000000–0x2003FFFF, "
            "peripherals 0x40000000–0xBFFFFFFF")


def _inside(region: Tuple[int, int], start: int, end: int) -> bool:
    return region[0] <= start and end <= region[0] + region[1]


class FakeMemory:
    def __init__(self, peripherals: List[PeripheralDef], registers: RegisterMemory, seed: int = 7) -> None:
        self._registers = registers
        self._by_address: Dict[int, str] = {r.address: r.full_name for p in peripherals for r in p.registers}
        self._pages: Dict[int, bytearray] = {}
        self._seed = seed
        self.reads = 0

    # ---- pages ------------------------------------------------------------------------------------------

    def _page(self, base: int) -> bytearray:
        page = self._pages.get(base)
        if page is None:
            rng = random.Random(self._seed * 1_000_003 + base)
            page = bytearray(rng.getrandbits(8) for _ in range(PAGE))
            self._seed_contents(base, page)
            self._pages[base] = page
        return page

    @staticmethod
    def _seed_contents(base: int, page: bytearray) -> None:
        """Recognisable contents: a vector table and a version string in flash, a banner in RAM."""
        if base == FLASH[0]:
            page[0:16] = struct.pack("<4I", RAM[0] + RAM[1], 0x0800_0141, 0x0800_01A5, 0x0800_01A7)
            text = b"Gecko Bootloader v2.4.1\x00rail_test 2026.10.1\x00"
            page[0x200:0x200 + len(text)] = text
        if base == RAM[0]:
            text = b"SiRAT fake RAM\x00\x00"
            page[0:16] = text
            page[16:32] = bytes(range(16))
            page[0x100:0x104] = b"\x00\x00\x00\x00"

    def _get(self, address: int, count: int) -> bytes:
        out = bytearray()
        while count > 0:
            base = address - address % PAGE
            offset = address - base
            take = min(count, PAGE - offset)
            out += self._page(base)[offset:offset + take]
            address += take
            count -= take
        return bytes(out)

    def _put(self, address: int, data: bytes) -> None:
        for i, byte in enumerate(data):
            base = (address + i) - (address + i) % PAGE
            self._page(base)[address + i - base] = byte

    # ---- reads ------------------------------------------------------------------------------------------

    def _region(self, start: int, end: int) -> str:
        for name, region in (("flash", FLASH), ("ram", RAM), ("peripherals", PERIPHERALS)):
            if _inside(region, start, end):
                return name
        raise ApiError(ErrorCode.OUT_OF_RANGE, f"0x{start:08X}–0x{end - 1:08X} isn't mapped ({MAP_TEXT})",
                       {"address": start})

    def read(self, address: int, size: int) -> Tuple[int, bytes]:
        """Aligns the start down and the end up to 4 bytes; returns (aligned address, data)."""
        if not 1 <= size <= 4096:
            raise ApiError(ErrorCode.INVALID_PARAMS, "size must be between 1 and 4096 bytes")
        start = address & ~3
        end = (address + size + 3) & ~3
        region = self._region(start, end)
        self.reads += 1
        if region == "ram" and start <= READ_COUNTER < end:
            self._put(READ_COUNTER, struct.pack("<I", self.reads & 0xFFFF_FFFF))
        if region == "peripherals":
            return start, b"".join(struct.pack("<I", self._register_word(a)) for a in range(start, end, 4))
        return start, self._get(start, end - start)

    def _register_word(self, address: int) -> int:
        name = self._by_address.get(address)
        if name is None:
            return 0
        reg = self._registers.get(name)
        return self._registers.values[name] if reg.access.readable else 0

    # ---- writes -----------------------------------------------------------------------------------------

    def write(self, address: int, value: int, size: int) -> int:
        """Read-modify-write of the aligned word; returns the read-back value of `size` bytes."""
        if size not in (1, 2, 4):
            raise ApiError(ErrorCode.INVALID_PARAMS, "size must be 1, 2 or 4")
        if not 0 <= value < 1 << (8 * size):
            raise ApiError(ErrorCode.OUT_OF_RANGE, f"0x{value:X} doesn't fit in {size} byte(s)")
        if crosses_word(address, size):
            raise ApiError(ErrorCode.INVALID_PARAMS, f"A {size}-byte write at 0x{address:08X} crosses a 4-byte word")
        word = address & ~3
        region = self._region(word, word + 4)
        if region == "flash":
            raise ApiError(ErrorCode.ACCESS_DENIED, "Flash can't be written with memory.write")
        offset = address - word
        if region == "peripherals":
            name = self._register_at(word)
            old = struct.pack("<I", self._registers.values[name])
            new = old[:offset] + value.to_bytes(size, "little") + old[offset + size:]
            self._registers.write(name, struct.unpack("<I", new)[0])
        else:
            self._put(address, value.to_bytes(size, "little"))
        _, data = self.read(word, 4)
        return int.from_bytes(data[offset:offset + size], "little")

    def _register_at(self, word: int) -> str:
        name: Optional[str] = self._by_address.get(word)
        if name is None:
            raise ApiError(ErrorCode.HARDWARE_ERROR, f"Bus fault: no register at 0x{word:08X}",
                           {"cause": "other"})
        return name
