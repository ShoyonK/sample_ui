"""Radio Calculator config files and the field-by-field comparison with the chip (req 21, req 12).

Config format: `PERIPHERAL.REGISTER.FIELD = value`, one per line, decimal or 0x hex, `#` starts a comment
(a whole line or the rest of a line).
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from sirat_ui.models.radio import ConfigEntry, RadioConfig

_LINE = re.compile(r"^(?P<p>[A-Za-z_]\w*)\.(?P<r>[A-Za-z_]\w*)\.(?P<f>[A-Za-z_]\w*)\s*=\s*(?P<v>\S+)$")

MATCH, MISMATCH, ERROR = "match", "mismatch", "error"
STATUS_TEXT = {MATCH: "✓ Match", MISMATCH: "⚠ Mismatch", ERROR: "❌ Error"}
COLUMNS = ["peripheral", "register", "field", "expected", "actual", "status"]
_STATUS_ORDER = {MISMATCH: 0, ERROR: 1, MATCH: 2}  # sorting by Status puts problems first


def parse_config(text: str, name: str = "config") -> RadioConfig:
    config = RadioConfig(name)
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = _LINE.match(line)
        try:
            if not match:
                raise ValueError
            config.entries.append(ConfigEntry(match["p"], match["r"], match["f"], int(match["v"], 0)))
        except ValueError:
            config.skipped.append(f"line {number}: {raw.strip()}")
    return config


@dataclass(frozen=True)
class FieldResult:
    entry: ConfigEntry
    actual: Optional[int]
    status: str
    note: str = ""  # why it's an error

    def row(self) -> Dict[str, Union[int, str]]:
        return {"peripheral": self.entry.peripheral, "register": self.entry.register, "field": self.entry.field,
                "expected": self.entry.expected, "actual": self.actual if self.actual is not None else -1,
                "status": self.status}

    @property
    def actual_text(self) -> str:
        return value_text(self.actual) if self.actual is not None else self.note


def value_text(value: int) -> str:
    """Small values in decimal, big ones also in hex (frequency words, masks)."""
    return str(value) if value < 256 else f"{value} (0x{value:X})"


def _sort_key(result: FieldResult, column: str) -> Tuple[int, str]:
    """Numbers sort as numbers, text as text (each column holds one kind)."""
    value = result.row()[column]
    return (value, "") if isinstance(value, int) else (0, value)


@dataclass
class RadioComparison:
    config_name: str
    results: List[FieldResult]

    @property
    def counts(self) -> Dict[str, int]:
        c = Counter(r.status for r in self.results)
        return {s: c.get(s, 0) for s in (MATCH, MISMATCH, ERROR)}

    @property
    def summary(self) -> str:
        c = self.counts
        return f"✓ {c[MATCH]} Matches | ⚠ {c[MISMATCH]} Mismatches | ❌ {c[ERROR]} Errors"

    def sorted(self, column: str, descending: bool = False) -> List[FieldResult]:
        """Req 21 "Sortable by any column". Ties keep the config file's order."""
        key = column if column in COLUMNS else "peripheral"
        if key == "status":
            return sorted(self.results, key=lambda r: _STATUS_ORDER[r.status], reverse=descending)
        return sorted(self.results, key=lambda r: _sort_key(r, key), reverse=descending)

    def report_csv(self) -> str:
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow([f"Radio Calculator comparison: {self.config_name}"])
        writer.writerow([self.summary])
        writer.writerow(["Peripheral", "Register", "Field", "Expected", "Actual", "Status"])
        for r in self.results:
            writer.writerow([r.entry.peripheral, r.entry.register, r.entry.field, r.entry.expected,
                             r.actual if r.actual is not None else r.note, r.status.capitalize()])
        return out.getvalue()
