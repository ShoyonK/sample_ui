"""Read all registers of a peripheral (req 4 context menu, req 5 peripheral mode).

Reads one register at a time so the progress dialog can show "Reading {periph}.{reg}..." and
"X of Y", and Cancel takes effect before the next register. Write-only and read-sensitive registers
(req 7: reading USART/I2C/SPI clears FIFOs and flags) are skipped. A lost DUT stops the run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.domains.logs.service import LogService
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.models.registers import PeripheralDef, RegisterDef

_STOP_CODES = (ErrorCode.DUT_DISCONNECTED, ErrorCode.WRONG_STATE)


@dataclass
class ReadAllJob:
    peripheral: str
    registers: List[RegisterDef]
    skipped_sensitive: int = 0
    index: int = 0
    ok: int = 0
    failed: int = 0
    current: str = ""
    cancelled: bool = False
    stopped_reason: str = ""
    finished: bool = False
    summary: str = ""

    @property
    def total(self) -> int:
        return len(self.registers)


class ReadAllService:
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
        if self.running:
            self.refused.emit()
            return False
        readable = [r for r in periph.registers if r.access.readable]
        targets = [r for r in readable if not r.read_sensitive]
        self.job = ReadAllJob(periph.name, targets, skipped_sensitive=len(readable) - len(targets))
        self._log.info(f"Reading all registers of {periph.name} ({len(targets)})…")
        self._next()
        return True

    def cancel(self) -> None:
        if self.job is not None and not self.job.finished:
            self.job.cancelled = True

    def _next(self) -> None:
        job = self.job
        if job is None or job.finished:
            return
        if job.cancelled or job.stopped_reason or job.index >= job.total:
            self._finish(job)
            return
        self._read_next(job)

    def _read_next(self, job: ReadAllJob) -> None:
        reg = job.registers[job.index]
        job.current = reg.full_name
        self.progress.emit(job)

        def done(_value: int) -> None:
            job.ok += 1
            advance()

        def failed(error: ApiError) -> None:
            job.failed += 1
            if error.code in _STOP_CODES:
                job.stopped_reason = error.message
            advance()

        def advance() -> None:
            job.index += 1
            self._next()

        self._registers.read(reg, manual=False, quiet=True).then(done, failed)

    def _finish(self, job: ReadAllJob) -> None:
        job.finished = True
        job.current = ""
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
