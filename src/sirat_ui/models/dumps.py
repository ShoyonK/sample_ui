"""Register dumps and their comparison (req 12)."""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

STAMP = "%Y%m%d_%H%M%S"
_UNSAFE = re.compile(r'[\\/:*?"<>|]')


@dataclass
class RegisterDump:
    name: str
    timestamp: dt.datetime
    description: str = ""
    values: Dict[str, int] = field(default_factory=dict)      # full_name -> value
    addresses: Dict[str, int] = field(default_factory=dict)   # full_name -> address (for the CSV)

    @property
    def peripherals(self) -> List[str]:
        return sorted({name.split(".", 1)[0] for name in self.values})

    @property
    def file_name(self) -> str:
        return f"{_UNSAFE.sub('_', self.name).strip() or 'dump'}_{self.timestamp.strftime(STAMP)}.csv"

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "timestamp": self.timestamp.isoformat(timespec="seconds"),
                "description": self.description,
                "values": {k: f"0x{v:08X}" for k, v in self.values.items()},
                "addresses": {k: f"0x{v:08X}" for k, v in self.addresses.items()}}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RegisterDump":
        return RegisterDump(str(data.get("name") or "dump"),
                            dt.datetime.fromisoformat(str(data.get("timestamp"))),
                            str(data.get("description") or ""),
                            {k: _int(v) for k, v in (data.get("values") or {}).items()},
                            {k: _int(v) for k, v in (data.get("addresses") or {}).items()})


def _int(value: Any) -> int:
    return value if isinstance(value, int) else int(str(value).strip(), 0)


@dataclass(frozen=True)
class DiffRow:
    register: str
    before: int
    after: int
    fields: Tuple[Tuple[str, int, int], ...] = ()  # (field, before, after) for fields that changed

    @property
    def change(self) -> str:
        """Field-level differences, e.g. "MODE 1→3, EN 1→0"; the changed bits when there are no fields."""
        if self.fields:
            return ", ".join(f"{name} {old}→{new}" for name, old, new in self.fields)
        return f"bits 0x{self.before ^ self.after:08X}"


@dataclass
class Comparison:
    title: str
    before_label: str
    after_label: str
    rows: List[DiffRow]
    compared: int
    only_in_one: int = 0
    errors: int = 0

    @property
    def summary(self) -> str:
        count = len(self.rows)
        text = f"{count} register{'' if count == 1 else 's'} differ{'s' if count == 1 else ''} · {self.compared} compared"
        if self.only_in_one:
            text += f" · {self.only_in_one} in only one"
        if self.errors:
            text += f" · {self.errors} couldn't be read"
        return text

    def report_csv(self) -> str:
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow([self.title])
        writer.writerow([self.summary])
        writer.writerow(["Register", self.before_label, self.after_label, "Change"])
        for row in self.rows:
            writer.writerow([row.register, f"0x{row.before:08X}", f"0x{row.after:08X}", row.change])
        return out.getvalue()
