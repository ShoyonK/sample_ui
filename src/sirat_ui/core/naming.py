"""Unique names for things the user saves (actions, sequences): load_phy, load_phy_2, load_phy_3 ..."""

from __future__ import annotations

from typing import Container


def unique_name(name: str, taken: Container[str], fallback: str) -> str:
    base = name.strip() or fallback
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    return candidate
