"""Reading registers one at a time, the loop behind Read all registers (req 4) and the dump reads (req 12, 21).

One read at a time lets a progress dialog show "Reading PERIPHERAL.REGISTER..." with "X of Y", and makes Cancel
take effect before the next register. A read that fails is counted and skipped; a lost DUT (or a switch to another
DUT) stops the job, keeping the first reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import Callable, Dict, List, TypeVar

from sibench_ui.domains.registers.service import RegisterService
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.models.registers import RegisterDef

STOP_CODES = (ErrorCode.DUT_DISCONNECTED, ErrorCode.WRONG_STATE)


@dataclass
class RegisterReadJob:
    """A list of registers being read in order.

    `failed` counts reads that failed; `cancelled` is the user's Cancel; `stopped_reason` says why the job ended
    early without the user asking (the DUT went away, the user switched DUT).
    """
    registers: List[RegisterDef]
    values: Dict[str, int] = field(default_factory=dict)   # full name -> value read
    index: int = 0
    failed: int = 0
    current: str = ""
    cancelled: bool = False
    stopped_reason: str = ""
    finished: bool = False

    @property
    def total(self) -> int:
        return len(self.registers)

    @property
    def running(self) -> bool:
        return not self.finished

    def cancel(self) -> None:
        if not self.finished:
            self.cancelled = True

    def stop(self, reason: str) -> None:
        """Ends the job as stopped before the next register, e.g. when the user switches DUT."""
        if not self.finished:
            self.stopped_reason = reason


J = TypeVar("J", bound=RegisterReadJob)


def read_one_by_one(registers: RegisterService, job: J, on_step: Callable[[J], None],
                    on_finish: Callable[[J], None]) -> None:
    """Reads the job's registers in order.

    Args:
        registers: Does the reads (quietly, without recording them in History).
        job: The job; updated as reads complete.
        on_step: Called before each read, with `current` set to the register being read.
        on_finish: Called once when the job ends (all read, cancelled or stopped), with `finished` set.
    """
    def run() -> None:
        while not (job.cancelled or job.stopped_reason or job.index >= job.total):
            reg = job.registers[job.index]
            job.current = reg.full_name
            on_step(job)
            call = registers.read(reg, manual=False, quiet=True).then(partial(read_ok, reg.full_name), read_failed)
            if call.pending:   # carry on when it answers; a read that answered at once just loops (no recursion)
                call.then(lambda _value: run(), lambda _error: run())
                return
        job.finished, job.current = True, ""
        on_finish(job)

    def read_ok(name: str, value: int) -> None:
        job.values[name] = value
        job.index += 1

    def read_failed(error: ApiError) -> None:
        job.failed += 1
        job.index += 1
        if error.code in STOP_CODES and not job.stopped_reason:   # keep the first reason (e.g. a DUT switch)
            job.stopped_reason = error.message

    run()
