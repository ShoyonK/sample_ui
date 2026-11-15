"""DumpService (req 12): take a dump, diff live values against a dump, compare two dump files, and
compare the chip with a Radio Calculator config (req 21).

Reads go one register at a time (domains/registers/sequential.py, like Read all) so the progress dialog can show
"Reading PERIPHERAL.REGISTER..." and Cancel stops before the next register. Write-only and
read-sensitive registers are skipped (req 7). Dumps taken this run are kept for sessions (req 34),
newest last, at most MAX_DUMPS.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from sirat_ui.core.dumps import compare, read_csv, write_csv
from sirat_ui.core.observable import Event
from sirat_ui.core.radio_config import ERROR, FieldResult, MATCH, MISMATCH, RadioComparison
from sirat_ui.domains.logs.service import LogService
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.registers.sequential import RegisterReadJob, read_one_by_one
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.models.dumps import Comparison, RegisterDump
from sirat_ui.models.radio import RadioConfig
from sirat_ui.models.registers import RegisterDef

MAX_DUMPS = 50  # req 12: "Limit to prevent unbounded growth"


@dataclass
class DumpFile:
    """A dump CSV in the dumps folder, as the file list shows it."""
    path: Path
    name: str
    timestamp: dt.datetime
    registers: int
    peripherals: List[str]


@dataclass(kw_only=True)   # keyword-only, so these stay required after the base class's defaulted fields
class DumpJob(RegisterReadJob):
    """The reads behind one dump, live diff or Radio Calculator diff; on_done gets it once it finishes."""
    kind: str  # "take" | "live" | "radio"
    on_done: Callable[["DumpJob"], None]


def readable(registers: Iterable[RegisterDef]) -> List[RegisterDef]:
    """The registers a dump reads: readable and not read-sensitive."""
    return [r for r in registers if r.access.readable and not r.read_sensitive]


class DumpService:
    """Dump files and the reads behind each kind of comparison (see the module docstring)."""

    def __init__(self, directory: Path, catalog: RegisterCatalog, registers: RegisterService, log: LogService,
                 clock: Callable[[], dt.datetime] = lambda: dt.datetime.now().replace(microsecond=0)) -> None:
        self.directory = Path(directory)
        self._catalog = catalog
        self._registers = registers
        self._log = log
        self._clock = clock
        self.dumps: List[RegisterDump] = []
        self.job: Optional[DumpJob] = None
        self.progress = Event()   # (job)
        self.changed = Event()    # dump files or session dumps changed

    @property
    def running(self) -> bool:
        return self.job is not None and not self.job.finished

    # ---- files --------------------------------------------------------------------------------

    def files(self) -> List[DumpFile]:
        """Dump CSVs in the dumps folder, newest first. Files that can't be read are left out."""
        out = []
        for path in self.directory.glob("*.csv") if self.directory.exists() else []:
            try:
                dump = read_csv(path)
            except (OSError, ValueError):
                continue
            out.append(DumpFile(path, dump.name, dump.timestamp, len(dump.values), dump.peripherals))
        return sorted(out, key=lambda f: (f.timestamp, f.name), reverse=True)

    def save(self, dump: RegisterDump) -> Path:
        path = write_csv(self.directory, dump)
        self.dumps = (self.dumps + [dump])[-MAX_DUMPS:]
        self._log.info(f"Saved dump {dump.name}: {len(dump.values)} registers to {path}")
        self.changed.emit()
        return path

    def delete(self, path: Path) -> None:
        Path(path).unlink(missing_ok=True)
        self._log.info(f"Deleted dump {Path(path).name}")
        self.changed.emit()

    def compare_files(self, first: Path, second: Path) -> Comparison:
        """The older dump is "before". Raises ValueError/OSError for unreadable files."""
        a, b = sorted((read_csv(first), read_csv(second)), key=lambda d: d.timestamp)
        return compare(a.values, b.values, self._catalog.register, title=f"{a.name} vs {b.name}",
                       before_label=f"{a.name} ({a.timestamp:%H:%M:%S})",
                       after_label=f"{b.name} ({b.timestamp:%H:%M:%S})")

    # ---- reading: take a dump / diff vs live ----------------------------------------------------

    def take(self, peripherals: List[str], on_done: Callable[[DumpJob], None]) -> bool:
        """Reads every dumpable register of the peripherals; on_done gets the job (see new_dump).

        Returns:
            False when another read is still running.
        """
        regs = [r for name in peripherals for r in readable(self._peripheral_registers(name))]
        return self._start(DumpJob(regs, kind="take", on_done=on_done), f"Taking a dump of {', '.join(peripherals)}")

    def diff_live(self, path: Path, on_done: Callable[[Optional[Comparison]], None]) -> bool:
        """Reads every register in the dump that the chip has; registers it doesn't have count as errors."""
        dump = read_csv(path)
        regs = [self._catalog.register(name) for name in dump.values]
        known = readable(r for r in regs if r is not None)
        missing = len(dump.values) - len(known)

        def finished(job: DumpJob) -> None:
            if job.cancelled or job.stopped_reason:
                on_done(None)
                return
            saved = {name: dump.values[name] for name in job.values}
            result = compare(saved, job.values, self._catalog.register, title=f"Live vs {dump.name}",
                             before_label=f"{dump.name} ({dump.timestamp:%H:%M:%S})", after_label="Live")
            result.errors = missing + job.failed
            on_done(result)

        return self._start(DumpJob(known, kind="live", on_done=finished), f"Comparing live values with {dump.name}")

    def radio_diff(self, config: RadioConfig, peripherals: List[str],
                   on_done: Callable[[Optional[RadioComparison]], None]) -> bool:
        """Req 21: reads each register the chosen fields live in once, then checks every field.

        Match: live == expected. Mismatch: they differ. Error: the register or field doesn't exist, can't be
        read (write-only, read-sensitive), or the read failed.
        """
        entries = [e for e in config.entries if e.peripheral in peripherals]
        problems: Dict[int, str] = {}
        to_read: Dict[str, RegisterDef] = {}
        for i, entry in enumerate(entries):
            reg = self._catalog.register(entry.register_name)
            if reg is None:
                problems[i] = "Register not found"
            elif reg.field(entry.field) is None:
                problems[i] = "Field not found"
            elif not reg.access.readable:
                problems[i] = "Write-only register"
            elif reg.read_sensitive:
                problems[i] = "Read-sensitive, not read"
            else:
                to_read.setdefault(reg.full_name, reg)

        def finished(job: DumpJob) -> None:
            if job.cancelled or job.stopped_reason:
                on_done(None)
                return
            results = []
            for i, entry in enumerate(entries):
                value = job.values.get(entry.register_name)
                if i in problems:
                    results.append(FieldResult(entry, None, ERROR, problems[i]))
                elif value is None:
                    results.append(FieldResult(entry, None, ERROR, "Read failed"))
                else:
                    fdef = to_read[entry.register_name].field(entry.field)
                    assert fdef is not None  # checked when to_read was built
                    actual = fdef.extract(value)
                    results.append(FieldResult(entry, actual, MATCH if actual == entry.expected else MISMATCH))
            comparison = RadioComparison(config.name, results)
            self._log.info(f"Radio Calculator diff with {config.name}: {comparison.summary}")
            on_done(comparison)

        return self._start(DumpJob(list(to_read.values()), kind="radio", on_done=finished),
                           f"Comparing with Radio Calculator config {config.name} ({len(entries)} fields)")

    def cancel(self) -> None:
        if self.job is not None:
            self.job.cancel()

    def stop(self, reason: str) -> None:
        """Ends the job as stopped (nothing is saved), e.g. when the user switches DUT."""
        if self.job is not None:
            self.job.stop(reason)

    def new_dump(self, job: DumpJob, name: str, description: str = "") -> RegisterDump:
        """The dump a finished "take" job read, with the registers' addresses for the CSV."""
        addresses = {r.full_name: r.address for r in job.registers if r.full_name in job.values}
        return RegisterDump(name, self._clock(), description, dict(job.values), addresses)

    def _peripheral_registers(self, name: str) -> Sequence[RegisterDef]:
        periph = self._catalog.peripheral(name)
        return periph.registers if periph else ()

    def _start(self, job: DumpJob, message: str) -> bool:
        if self.running:
            return False
        self.job = job
        self._log.info(f"{message} ({job.total} registers)…")
        read_one_by_one(self._registers, job, self.progress.emit, self._finished)
        return True

    def _finished(self, job: DumpJob) -> None:
        self.progress.emit(job)
        job.on_done(job)

    # ---- sessions (req 34) ---------------------------------------------------------------------

    def to_records(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.dumps]

    def restore(self, records: List[Dict[str, Any]]) -> None:
        """A loaded session brings its dumps back; files missing from the dumps folder are rewritten."""
        dumps = []
        for record in records or []:
            try:
                dumps.append(RegisterDump.from_dict(record))
            except (TypeError, ValueError):
                continue
        self.dumps = dumps[-MAX_DUMPS:]
        for dump in self.dumps:
            if not (self.directory / dump.file_name).exists():
                write_csv(self.directory, dump)
        self.changed.emit()
