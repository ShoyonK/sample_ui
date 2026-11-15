"""Parse and format register values (req §5: Hex/Dec/Bin)."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ValueFormat(str, Enum):
    """How register values are shown and, for bare digits, parsed."""
    HEX = "hex"
    DEC = "dec"
    BIN = "bin"

    @classmethod
    def from_index(cls, index: int) -> "ValueFormat":
        """The format at a segmented-control index, clamped to the valid range."""
        members = list(cls)
        return members[max(0, min(index, len(members) - 1))]

    @property
    def ordinal(self) -> int:
        """0, 1, 2 for the Hex/Dec/Bin segmented control. (Not `index`, which str already defines.)"""
        return list(ValueFormat).index(self)


_BASES = {ValueFormat.HEX: 16, ValueFormat.DEC: 10, ValueFormat.BIN: 2}

NOT_READ = "─"


def format_value(value: int, fmt: ValueFormat = ValueFormat.HEX, width: int = 32) -> str:
    """Formats a register value: 0x-padded hex, decimal, or 0b binary in groups of 8 bits."""
    if fmt == ValueFormat.DEC:
        return str(value)
    if fmt == ValueFormat.BIN:
        digits = f"{value:0{width}b}"
        groups = [digits[i:i + 8] for i in range(0, len(digits), 8)]
        return "0b" + "_".join(groups)
    return f"0x{value:0{max(1, width // 4)}X}"


def parse_seconds(text: str) -> Optional[float]:
    """A typed interval such as "0.5" or "2 s"; None when it isn't a number."""
    try:
        return float(text.replace("s", "").strip())
    except ValueError:
        return None


def format_field(value: int) -> str:
    return f"0x{value:X}"


def parse_value(text: str, default: ValueFormat = ValueFormat.HEX) -> int:
    """Parses a typed value. 0x/0b/0o prefixes win; bare digits are read in `default`. Spaces and _ are ignored.

    Raises:
        ValueError: The text is empty, negative or not a number in that base (the message is user-facing).
    """
    cleaned = (text or "").strip().replace("_", "").replace(" ", "").lower()
    if not cleaned:
        raise ValueError("Enter a value")
    if cleaned.startswith("-"):
        raise ValueError("Negative values aren't allowed")
    try:
        if cleaned.startswith("0x"):
            return int(cleaned[2:], 16)
        if cleaned.startswith("0b"):
            return int(cleaned[2:], 2)
        if cleaned.startswith("0o"):
            return int(cleaned[2:], 8)
        return int(cleaned, _BASES[default])
    except ValueError:
        raise ValueError(f"'{text.strip()}' isn't a valid {default.value} value") from None
