"""Memory viewer helpers (req 19): number parsing, alignment and the hex dump in bytes, words or dwords.

The station aligns reads to 4 bytes and returns the aligned start; everything here is little-endian.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sirat_ui.models.memory import DumpRow

FORMATS = ("Bytes", "Words", "DWords")
UNIT = {"Bytes": 1, "Words": 2, "DWords": 4}
PER_LINE = {"Bytes": 16, "Words": 8, "DWords": 4}   # units per line (req 19 "Memory Display Format")
WRITE_SIZES = (("Byte", 1), ("Word", 2), ("DWord", 4))
MAX_READ = 4096


def parse_number(text: str) -> Optional[int]:
    """0x-prefixed hex or decimal, underscores allowed; None when it isn't a non-negative number."""
    s = text.strip().replace("_", "").lower()
    try:
        value = int(s[2:], 16) if s.startswith("0x") else int(s, 10)
    except ValueError:
        return None
    return value if value >= 0 else None


def address_problem(text: str) -> str:
    value = parse_number(text)
    if value is None:
        return "Enter an address in hex (0x20000000) or decimal"
    if value > 0xFFFF_FFFF:
        return "Addresses are 32-bit"
    return ""


def size_problem(text: str) -> str:
    value = parse_number(text)
    if value is None or not 1 <= value <= MAX_READ:
        return f"Size is 1 to {MAX_READ} bytes"
    return ""


def crosses_word(address: int, size: int) -> bool:
    return address % 4 + size > 4


def write_problem(address_text: str, value_text: str, size: int) -> str:
    problem = address_problem(address_text)
    if problem:
        return problem
    value = parse_number(value_text)
    if value is None:
        return "Enter a value in hex (0xFF) or decimal"
    if value >= 1 << (8 * size):
        return f"0x{value:X} doesn't fit in {size} byte{'s' if size > 1 else ''}"
    address = parse_number(address_text) or 0
    if crosses_word(address, size):
        return f"A {size}-byte write must stay inside one 4-byte word (try 0x{address & ~(size - 1):08X})"
    return ""


def aligned_range(address: int, size: int) -> Tuple[int, int]:
    """(start, length) of what the station actually reads."""
    start = address & ~3
    return start, ((address + size + 3) & ~3) - start


def _ascii(chunk: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)


def rows(address: int, data: bytes, fmt: str, previous: Optional[Tuple[int, bytes]] = None) -> List[DumpRow]:
    unit, per_line = UNIT[fmt], PER_LINE[fmt]
    line_bytes = unit * per_line
    old_start, old = previous or (0, b"")

    def changed(at: int) -> bool:
        i = at - old_start
        return bool(old) and 0 <= i and i + unit <= len(old) and old[i:i + unit] != data[at - address:at - address + unit]

    out = []
    for offset in range(0, len(data), line_bytes):
        chunk = data[offset:offset + line_bytes]
        cells = []
        for i in range(0, len(chunk) - len(chunk) % unit, unit):
            value = int.from_bytes(chunk[i:i + unit], "little")
            text = f"{value:02X}" if unit == 1 else f"0x{value:0{unit * 2}X}"
            cells.append((text, changed(address + offset + i)))
        out.append(DumpRow(address + offset, tuple(cells), _ascii(chunk) if unit == 1 else ""))
    return out


def row_text(row: DumpRow) -> str:
    cells = [text for text, _ in row.cells]
    if cells and len(cells[0]) == 2:   # bytes: 8 + 8 and the ASCII column
        hex_part = " ".join(cells[:8]) + ("  " + " ".join(cells[8:]) if len(cells) > 8 else "")
        return f"0x{row.address:08X}: {hex_part.ljust(48)}  |{row.ascii}|"
    return f"0x{row.address:08X}: " + " ".join(cells)


def dump_text(address: int, data: bytes, fmt: str) -> str:
    """The req 19 text layout, for copying."""
    return "\n".join([f"Address: 0x{address:08X}"] + [row_text(r) for r in rows(address, data, fmt)])
