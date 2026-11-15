"""The one-register-at-a-time read loop behind Read all and the dump reads (domains/registers/sequential.py)."""

import sys

from sirat_ui.domains.registers.sequential import RegisterReadJob, read_one_by_one
from sirat_ui.gateway.call import Call
from sirat_ui.models.registers import RegisterDef


class InstantRegisters:
    """Answers every read at once, like the fake station with no latency."""

    def read(self, reg, manual=True, quiet=False):
        return Call.succeeded(reg.address)


def test_reads_that_answer_at_once_do_not_recurse_per_register():
    regs = [RegisterDef("BIG", f"R{i}", i) for i in range(sys.getrecursionlimit() * 2)]
    job = RegisterReadJob(regs)
    finished = []
    read_one_by_one(InstantRegisters(), job, lambda j: None, finished.append)   # type: ignore[arg-type]
    assert finished == [job] and job.finished and len(job.values) == len(regs) and job.failed == 0
