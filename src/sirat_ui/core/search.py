"""Peripheral/register/field filtering (req §6 matching algorithm)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from sirat_ui.core.registers import PeripheralDef


@dataclass
class SearchResult:
    peripherals: List[str] = field(default_factory=list)
    # None means "show every register of this peripheral"
    registers: Dict[str, Optional[List[str]]] = field(default_factory=dict)
    expanded: Set[str] = field(default_factory=set)
    auto_select: Optional[str] = None
    is_empty_query: bool = True


def visible_peripherals(peripherals: Iterable[PeripheralDef], show_secure: bool) -> List[PeripheralDef]:
    items = [p for p in peripherals if show_secure or not p.is_secure_variant]
    return sorted(items, key=lambda p: p.name)


def search(peripherals: Iterable[PeripheralDef], text: str, show_secure: bool) -> SearchResult:
    candidates = visible_peripherals(peripherals, show_secure)
    query = (text or "").strip().lower()
    if not query:
        return SearchResult(
            peripherals=[p.name for p in candidates],
            registers={p.name: None for p in candidates},
            is_empty_query=True,
        )

    result = SearchResult(is_empty_query=False)
    matched_registers: List[str] = []
    for periph in candidates:
        if query in periph.name.lower():
            result.peripherals.append(periph.name)
            result.registers[periph.name] = None
            result.expanded.add(periph.name)
            continue
        hits = []
        for reg in periph.registers:
            if query in reg.name.lower() or any(query in f.name.lower() for f in reg.fields):
                hits.append(reg.name)
                matched_registers.append(reg.full_name)
        if hits:
            result.peripherals.append(periph.name)
            result.registers[periph.name] = hits
            result.expanded.add(periph.name)

    if len(matched_registers) == 1 and all(v is not None for v in result.registers.values()):
        result.auto_select = matched_registers[0]
    return result
