"""Operation history (req §9). Only manual reads and all writes are recorded."""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sirat_ui.core.observable import Event


@dataclass
class HistoryEntry:
    id: int
    ts: float
    operation: str            # READ | WRITE
    target: str               # REG or REG.FIELD
    value: int
    register: str
    field: Optional[str] = None
    register_value: Optional[int] = None

    def as_op(self) -> Dict[str, Any]:
        op: Dict[str, Any] = {"register": self.register, "value": self.value}
        if self.field:
            op["field"] = self.field
        return op


@dataclass
class HistoryLog:
    clock: Callable[[], float] = time.time
    entries: List[HistoryEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.changed = Event()
        self._ids = itertools.count(1)

    def record(self, operation: str, register: str, value: int, field_name: Optional[str] = None,
               register_value: Optional[int] = None) -> HistoryEntry:
        target = f"{register}.{field_name}" if field_name else register
        entry = HistoryEntry(next(self._ids), self.clock(), operation, target, value, register, field_name,
                             register_value)
        self.entries.append(entry)
        self.changed.emit()
        return entry

    def clear(self) -> None:
        self.entries.clear()
        self.changed.emit()

    def to_records(self) -> List[Dict[str, Any]]:
        """Req 34 session "history": the req 9 export fields plus time and full register value."""
        return [{"ts": e.ts, "operation": e.operation.lower(), "register": e.register, "field": e.field,
                 "value": e.value, "register_value": e.register_value} for e in self.entries]

    def restore(self, records: List[Dict[str, Any]]) -> None:
        """Replaces the history with saved records (sessions and auto-save)."""
        self.entries = []
        for r in records:
            if not isinstance(r, dict) or "register" not in r or "value" not in r:
                continue
            self.entries.append(HistoryEntry(
                next(self._ids), float(r.get("ts", self.clock())), str(r.get("operation", "read")).upper(),
                f"{r['register']}.{r['field']}" if r.get("field") else r["register"], int(r["value"]),
                r["register"], r.get("field"), r.get("register_value")))
        self.changed.emit()

    def by_ids(self, ids) -> List[HistoryEntry]:
        wanted = set(ids)
        return [e for e in self.entries if e.id in wanted]

    def as_text(self) -> str:
        lines = []
        for e in self.entries:
            stamp = time.strftime("%H:%M:%S", time.localtime(e.ts))
            lines.append(f"{stamp}\t{e.operation}\t{e.target}\t0x{e.value:X}")
        return "\n".join(lines)
