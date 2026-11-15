"""Read all registers of a peripheral (req 4 context menu, req 5 peripheral mode).

Reads one register at a time (domains/registers/sequential.py) so the progress dialog can show
"Reading {periph}.{reg}..." and "X of Y", and Cancel takes effect before the next register. Write-only and
read-sensitive registers (req 7: reading USART/I2C/SPI clears FIFOs and flags) are skipped. A lost DUT stops the run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sibench_ui.core.observable import Event
from sibench_ui.domains.logs.service import LogService
from sibench_ui.domains.registers.sequential import RegisterReadJob, read_one_by_one
from sibench_ui.domains.registers.service import RegisterService
from sibench_ui.models.registers import PeripheralDef


@dataclass(kw_only=True)   # keyword-only, so `peripheral` stays required after the base class's defaulted fields
class ReadAllJob(RegisterReadJob):
    """A read-all of one peripheral; `summary` is set when it finishes."""
    peripheral: str
    skipped_sensitive: int = 0
    summary: str = ""

    @property
    def ok(self) -> int:
        """How many registers were read."""
        return len(self.values)


class ReadAllService:
    """Runs one read-all at a time and reports progress through `progress` (a finished job carries its summary)."""

    def __init__(self, registers: RegisterService, log: LogService) -> None:
        self._registers = registers
        self._log = log
        self.job: Optional[ReadAllJob] = None
        self.progress = Event()  # (job); a finished job carries its summary
        self.refused = Event()   # start() while a read-all is already running

    @property
    def running(self) -> bool:
        return self.job is not None and not self.job.finished

    def start(self, periph: PeripheralDef) -> bool:
        """Starts reading the peripheral's readable registers. Returns False (and emits `refused`) while one runs."""
        if self.running:
            self.refused.emit()
            return False
        readable = [r for r in periph.registers if r.access.readable]
        targets = [r for r in readable if not r.read_sensitive]
        self.job = ReadAllJob(targets, peripheral=periph.name, skipped_sensitive=len(readable) - len(targets))
        self._log.info(f"Reading all registers of {periph.name} ({len(targets)})…")
        read_one_by_one(self._registers, self.job, self.progress.emit, self._finish)
        return True

    def cancel(self) -> None:
        if self.job is not None:
            self.job.cancel()

    def stop(self, reason: str) -> None:
        """Ends the job as stopped, e.g. when the user switches DUT."""
        if self.job is not None:
            self.job.stop(reason)

    def _finish(self, job: ReadAllJob) -> None:
        summary = f"{job.peripheral}: {job.ok} registers read, {job.failed} failed"
        if job.skipped_sensitive:
            summary += f", {job.skipped_sensitive} read-sensitive skipped"
        if job.cancelled:
            summary += " (cancelled)"
        if job.stopped_reason:
            summary += f" (stopped: {job.stopped_reason})"
        job.summary = summary
        self._log.info(summary)
        self.progress.emit(job)
