"""Operation history (req §9). Only manual reads and all writes are recorded."""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from sirat_ui.core.observable import Event

READ, WRITE = "READ", "WRITE"


def _target(register: str, field: Optional[str]) -> str:
    return f"{register}.{field}" if field else register


@dataclass
class HistoryEntry:
    """One read or write. `value` is the field value for a field write, else the register value;
    `register_value` is the whole register after a field write."""
    id: int
    ts: float
    operation: str            # READ | WRITE
    target: str               # REG or REG.FIELD
    value: int
    register: str
    field: Optional[str] = None
    register_value: Optional[int] = None

    def as_op(self) -> Dict[str, Any]:
        """The entry as an action op (register or field write)."""
        op: Dict[str, Any] = {"register": self.register, "value": self.value}
        if self.field:
            op["field"] = self.field
        return op


class HistoryLog:
    """The operation history: manual reads and all writes, oldest first (in memory; sessions save it)."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self.entries: List[HistoryEntry] = []
        self.changed = Event()
        self._ids = itertools.count(1)

    def record(self, operation: str, register: str, value: int, field_name: Optional[str] = None,
               register_value: Optional[int] = None) -> HistoryEntry:
        """Adds an entry. operation is READ or WRITE."""
        entry = HistoryEntry(next(self._ids), self.clock(), operation, _target(register, field_name), value, register,
                             field_name, register_value)
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
                _target(r["register"], r.get("field")), int(r["value"]), r["register"], r.get("field"),
                r.get("register_value")))
        self.changed.emit()

    def by_ids(self, ids: Iterable[Any]) -> List[HistoryEntry]:
        wanted = set(ids)
        return [e for e in self.entries if e.id in wanted]

    def as_text(self) -> str:
        lines = []
        for e in self.entries:
            stamp = time.strftime("%H:%M:%S", time.localtime(e.ts))
            lines.append(f"{stamp}\t{e.operation}\t{e.target}\t0x{e.value:X}")
        return "\n".join(lines)
