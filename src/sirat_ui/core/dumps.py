"""Register dumps (req 12): the dump record, its CSV file format, and comparing two sets of values.

CSV (req 12 "Dump File Format"): Peripheral,Register,Address,Value with hex address and value.
File names are `<name>_<YYYYMMDD_HHMMSS>.csv`; the name and time are read back from the file name.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Set

from sirat_ui.models.dumps import Comparison, DiffRow, RegisterDump, STAMP
from sirat_ui.models.registers import RegisterDef

CSV_HEADER = ["Peripheral", "Register", "Address", "Value"]
_FILE_RE = re.compile(r"^(?P<name>.*)_(?P<stamp>\d{8}_\d{6})$")


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
