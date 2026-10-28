"""The progress dialog for register reads that take a while: Take a dump, Diff vs live, Radio Calculator diff."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.dumps.service import DumpJob, DumpService
from sirat_ui.shared.viewmodel import BaseViewModel, qprop


class DumpProgressViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: DumpService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._progress_open = False
        self._progress_title = ""
        self._progress_label = ""
        self._count_text = ""
        self._progress = 0.0
        self._cancelling = False
        service.progress.connect(self._on_progress)

    progressOpen = qprop(bool, "_progress_open", changed)
    progressTitle = qprop(str, "_progress_title", changed)
    progressLabel = qprop(str, "_progress_label", changed)
    countText = qprop(str, "_count_text", changed)
    progress = qprop(float, "_progress", changed)
    cancelling = qprop(bool, "_cancelling", changed)

    def begin(self, title: str) -> None:
        self._update(progress_title=title)

    def _on_progress(self, job: DumpJob) -> None:
        if job.finished:
            self._update(progress_open=False, cancelling=False)
            return
        verb = "Comparing" if job.kind == "radio" else "Reading"
        self._update(progress_open=True, progress_label=f"{verb} {job.current}…",
                     count_text=f"{job.index + 1} of {job.total}",
                     progress=job.index / job.total if job.total else 0.0, cancelling=job.cancelled)

    @pyqtSlot()
    def cancel(self) -> None:
        self._service.cancel()
        self._update(cancelling=True, progress_label="Cancelling after this register…")
