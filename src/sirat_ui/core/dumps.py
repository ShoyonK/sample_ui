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
from typing import Callable, Dict, Optional

from sirat_ui.models.dumps import Comparison, DiffRow, RegisterDump, STAMP
from sirat_ui.models.registers import RegisterDef

CSV_HEADER = ["Peripheral", "Register", "Address", "Value"]
_FILE_RE = re.compile(r"^(?P<name>.*)_(?P<stamp>\d{8}_\d{6})$")


def _peripheral(full_name: str) -> str:
    return full_name.split(".", 1)[0]


def to_csv(dump: RegisterDump) -> str:
    """The dump in the req 12 CSV format, header first."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for full_name, value in dump.values.items():
        periph, _, reg = full_name.partition(".")
        writer.writerow([periph, reg, f"0x{dump.addresses.get(full_name, 0):08X}", f"0x{value:08X}"])
    return out.getvalue()


def write_csv(directory: Path, dump: RegisterDump) -> Path:
    """Writes the dump as `<name>_<stamp>.csv` in `directory` (created if needed) and returns the path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / dump.file_name
    path.write_text(to_csv(dump), encoding="utf-8")
    return path


def read_csv(path: Path) -> RegisterDump:
    """Reads a dump CSV. The name and time come from the file name, or the file's mtime when it has none.

    Raises:
        ValueError: The file isn't a register dump, or a row isn't Peripheral,Register,Address,Value.
        OSError: The file can't be read.
    """
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
    """Req 12: compares the registers of the peripherals both sides have; rows only for differences.

    Args:
        before: Register full name -> value, the older side.
        after: Register full name -> value, the newer side.
        lookup: Finds a register's definition, so a row can say which fields changed. Registers it doesn't know
            get a row without field detail.
        title: The comparison's title (shown above the table and in the report).
        before_label: Column heading for `before`.
        after_label: Column heading for `after`.

    Returns:
        The comparison, with how many registers were compared and how many exist on one side only.
    """
    common_periphs = {_peripheral(n) for n in before} & {_peripheral(n) for n in after}
    b = {n for n in before if _peripheral(n) in common_periphs}
    a = {n for n in after if _peripheral(n) in common_periphs}
    rows = []
    for name in sorted(b & a):
        if before[name] != after[name]:
            reg = lookup(name)
            pairs = ((f.name, f.extract(before[name]), f.extract(after[name])) for f in (reg.fields if reg else ()))
            fields = tuple(p for p in pairs if p[1] != p[2])
            rows.append(DiffRow(name, before[name], after[name], fields))
    return Comparison(title, before_label, after_label, rows, compared=len(b & a), only_in_one=len(b ^ a))
