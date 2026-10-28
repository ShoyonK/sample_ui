"""Parse and format register values (req §5: Hex/Dec/Bin)."""

from __future__ import annotations

from enum import Enum


class ValueFormat(str, Enum):
    HEX = "hex"
    DEC = "dec"
    BIN = "bin"

    @classmethod
    def from_index(cls, index: int) -> "ValueFormat":
        return list(cls)[max(0, min(index, 2))]

    @property
    def ordinal(self) -> int:
        """0, 1, 2 for the Hex/Dec/Bin segmented control. (Not `index`, which str already defines.)"""
        return list(ValueFormat).index(self)


NOT_READ = "─"


def format_value(value: int, fmt: ValueFormat = ValueFormat.HEX, width: int = 32) -> str:
    if fmt == ValueFormat.DEC:
        return str(value)
    if fmt == ValueFormat.BIN:
        digits = f"{value:0{width}b}"
        groups = [digits[i:i + 8] for i in range(0, len(digits), 8)]
        return "0b" + "_".join(groups)
    return f"0x{value:0{max(1, width // 4)}X}"


def format_field(value: int) -> str:
    return f"0x{value:X}"


_BASES = {ValueFormat.HEX: 16, ValueFormat.DEC: 10, ValueFormat.BIN: 2}


def parse_value(text: str, default: ValueFormat = ValueFormat.HEX) -> int:
    """Accepts 0x/0b/0o prefixes; bare digits use the currently selected format."""
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
