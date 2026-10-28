"""Progress dialog for Read all registers (req 4: modal, cancelable, "Reading {periph}.{reg}...", X of Y)."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.registers.read_all import ReadAllJob, ReadAllService
from sirat_ui.shared.viewmodel import BaseViewModel, qprop


class ReadAllViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: ReadAllService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._open = False
        self._label = ""
        self._count_text = ""
        self._progress = 0.0
        self._cancelling = False
        service.progress.connect(self._on_progress)

    isOpen = qprop(bool, "_open", changed)
    label = qprop(str, "_label", changed)
    countText = qprop(str, "_count_text", changed)
    progress = qprop(float, "_progress", changed)
    cancelling = qprop(bool, "_cancelling", changed)

    def _on_progress(self, job: ReadAllJob) -> None:
        if job.finished:
            self._update(open=False, cancelling=False)
            return
        self._update(open=True, label=f"Reading {job.current}…",
                     count_text=f"{job.index + 1} of {job.total}",
                     progress=job.index / job.total if job.total else 0.0, cancelling=job.cancelled)

    @pyqtSlot()
    def cancel(self) -> None:
        self._service.cancel()
        self._update(cancelling=True, label="Cancelling after this register…")
