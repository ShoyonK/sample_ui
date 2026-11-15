"""Progress dialog for Read all registers (req 4: modal, cancelable, "Reading {periph}.{reg}...", X of Y)."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject

from sibench_ui.domains.registers.read_all import ReadAllJob, ReadAllService
from sibench_ui.domains.registers.read_progress_viewmodel import ReadProgressViewModel
from sibench_ui.shared.interactions import InteractionService


class ReadAllViewModel(ReadProgressViewModel):
    """The Read all progress dialog; a finished job's summary is toasted."""

    def __init__(self, service: ReadAllService, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__("Reading registers", parent)
        self._service = service
        self._interactions = interactions
        service.progress.connect(self._on_progress)
        service.refused.connect(lambda: interactions.toast("error", "A read-all is already running"))

    def _on_progress(self, job: ReadAllJob) -> None:
        if job.finished:
            self.close()
            self._interactions.toast("error" if job.stopped_reason else "info", job.summary)
        else:
            self.show_step(job)

    def _cancel_job(self) -> None:
        self._service.cancel()
