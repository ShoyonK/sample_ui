"""One line of the memory viewer's hex dump (req 19)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DumpRow:
    """One line of the memory viewer: the address, its cells and (bytes only) ASCII."""
    address: int
    cells: Tuple[Tuple[str, bool], ...]     # (text, changed since the previous read)
    ascii: str                              # bytes format only
