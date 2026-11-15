"""Names and counts in user-facing text: unique names for things the user saves (load_phy, load_phy_2 ...) and
plurals ("3 registers")."""

from __future__ import annotations

from typing import Container, Optional


def unique_name(name: str, taken: Container[str], fallback: str) -> str:
    """`name`, or `name_2`, `name_3` ... until it isn't in `taken`. An empty name becomes `fallback`."""
    base = name.strip() or fallback
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    return candidate


def count(n: int, singular: str, plural: Optional[str] = None) -> str:
    """'1 note', '2 notes'. `plural` is for words that don't just add an s ('entry', 'entries')."""
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"
