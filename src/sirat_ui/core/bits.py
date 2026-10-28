"""Bit-level helpers for register and field values."""

from __future__ import annotations


def mask(width: int) -> int:
    return (1 << width) - 1


def extract(value: int, lsb: int, width: int) -> int:
    return (value >> lsb) & mask(width)


def insert(value: int, lsb: int, width: int, field_value: int) -> int:
    if field_value < 0 or field_value > mask(width):
        raise ValueError(f"Value 0x{field_value:X} doesn't fit in {width} bit(s) (max 0x{mask(width):X})")
    cleared = value & ~(mask(width) << lsb)
    return cleared | (field_value << lsb)


def toggle(value: int, bit: int) -> int:
    return value ^ (1 << bit)


def bit_list(value: int, width: int = 32) -> list:
    """Index i holds bit i."""
    return [bool((value >> i) & 1) for i in range(width)]


def bit_reverse(value: int, bits: int) -> int:
    return int(format(value, f"0{bits}b")[::-1], 2)
