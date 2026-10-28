"""Register dumps (req 12): the dump record, its CSV file format, and comparing two sets of values.

CSV (req 12 "Dump File Format"): Peripheral,Register,Address,Value with hex address and value.
File names are `<name>_<YYYYMMDD_HHMMSS>.csv`; the name and time are read back from the file name.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from sirat_ui.core.registers import RegisterDef

CSV_HEADER = ["Peripheral", "Register", "Address", "Value"]
STAMP = "%Y%m%d_%H%M%S"
_FILE_RE = re.compile(r"^(?P<name>.*)_(?P<stamp>\d{8}_\d{6})$")
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


def to_csv(dump: RegisterDump) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for full_name, value in dump.values.items():
        periph, _, reg = full_name.partition(".")
        writer.writerow([periph, reg, f"0x{dump.addresses.get(full_name, 0):08X}", f"0x{value:08X}"])
    return out.getvalue()


def write_csv(directory: Path, dump: RegisterDump) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / dump.file_name
    path.write_text(to_csv(dump), encoding="utf-8")
    return path


def read_csv(path: Path) -> RegisterDump:
    """Raises ValueError for a file that isn't a dump."""
    path = Path(path)
    match = _FILE_RE.match(path.stem)
    if match:
        name, stamp = match["name"], dt.datetime.strptime(match["stamp"], STAMP)
    else:
        name, stamp = path.stem, dt.datetime.fromtimestamp(path.stat().st_mtime).replace(microsecond=0)
    dump = RegisterDump(name, stamp)
    rows = csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig")))
    header = next(rows, None)
    if [h.strip() for h in header or []][:4] != CSV_HEADER:
        raise ValueError(f"{path.name} isn't a register dump (expected columns {', '.join(CSV_HEADER)})")
    for line, row in enumerate(rows, start=2):
        if not row:
            continue
        try:
            periph, reg, address, value = (cell.strip() for cell in row[:4])
            full_name = f"{periph}.{reg}"
            dump.values[full_name] = int(value, 0)
            dump.addresses[full_name] = int(address, 0)
        except ValueError:
            raise ValueError(f"{path.name} line {line}: expected Peripheral,Register,Address,Value") from None
    return dump


# ---- comparing ----------------------------------------------------------------------------------

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


def compare(before: Dict[str, int], after: Dict[str, int],
            lookup: Callable[[str], Optional[RegisterDef]], *, title: str, before_label: str,
            after_label: str) -> Comparison:
    """Req 12: compares registers of the peripherals both sides have; rows only for differences."""
    common_periphs = {n.split(".", 1)[0] for n in before} & {n.split(".", 1)[0] for n in after}
    def in_scope(names: Iterable[str]) -> Set[str]:
        return {n for n in names if n.split(".", 1)[0] in common_periphs}

    b, a = in_scope(before), in_scope(after)
    rows = []
    for name in sorted(b & a):
        if before[name] != after[name]:
            reg = lookup(name)
            fields = tuple((f.name, f.extract(before[name]), f.extract(after[name]))
                           for f in (reg.fields if reg else ()) if f.extract(before[name]) != f.extract(after[name]))
            rows.append(DiffRow(name, before[name], after[name], fields))
    return Comparison(title, before_label, after_label, rows, compared=len(b & a), only_in_one=len(b ^ a))
