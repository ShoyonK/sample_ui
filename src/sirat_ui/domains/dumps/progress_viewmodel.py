"""The progress dialog for register reads that take a while: Take a dump, Diff vs live, Radio Calculator diff."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject

from sirat_ui.domains.dumps.service import DumpJob, DumpService
from sirat_ui.domains.registers.read_progress_viewmodel import ReadProgressViewModel


class DumpProgressViewModel(ReadProgressViewModel):
    """The progress dialog for DumpService's reads; begin() sets the title for the next job."""

    def __init__(self, service: DumpService, parent: Optional[QObject] = None) -> None:
        super().__init__("", parent)
        self._service = service
        service.progress.connect(self._on_progress)

    def begin(self, title: str) -> None:
        self._update(title=title)

    def _on_progress(self, job: DumpJob) -> None:
        if job.finished:
            self.close()
        else:
            self.show_step(job, "Comparing" if job.kind == "radio" else "Reading")

    def _cancel_job(self) -> None:
        self._service.cancel()
