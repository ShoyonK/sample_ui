"""The progress dialog shared by register reads that take a while: Read all (req 4) and the dump reads (req 12, 21).

The dialog shows a title, "Reading PERIPHERAL.REGISTER…", "X of Y", a bar and Cancel. Subclasses connect their
service's progress to show_step() and close(), and say what Cancel does.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.registers.sequential import RegisterReadJob
from sirat_ui.shared.viewmodel import BaseViewModel, qprop


class ReadProgressViewModel(BaseViewModel):
    """A progress dialog for a RegisterReadJob (see the module docstring)."""

    changed = pyqtSignal()

    def __init__(self, title: str = "", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._open = False
        self._title = title
        self._label = ""
        self._count_text = ""
        self._progress = 0.0
        self._cancelling = False

    isOpen = qprop(bool, "_open", changed)
    title = qprop(str, "_title", changed)
    label = qprop(str, "_label", changed)
    countText = qprop(str, "_count_text", changed)
    progress = qprop(float, "_progress", changed)
    cancelling = qprop(bool, "_cancelling", changed)

    def show_step(self, job: RegisterReadJob, verb: str = "Reading") -> None:
        """Opens the dialog (if it isn't open) on the register the job is reading now."""
        self._update(open=True, label=f"{verb} {job.current}…", count_text=f"{job.index + 1} of {job.total}",
                     progress=job.index / job.total if job.total else 0.0, cancelling=job.cancelled)

    def close(self) -> None:
        self._update(open=False, cancelling=False)

    def _cancel_job(self) -> None:
        """Asks the service to stop before the next register."""
        raise NotImplementedError

    @pyqtSlot()
    def cancel(self) -> None:
        self._cancel_job()
        self._update(cancelling=True, label="Cancelling after this register…")
