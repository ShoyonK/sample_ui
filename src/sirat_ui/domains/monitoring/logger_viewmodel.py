"""Data logger panel (req 17)."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import List, Optional, Tuple

import time
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.thinning import thin
from sirat_ui.domains.monitoring.logger import RATE_MAX_S, RATE_MIN_S, DataLoggerService, Series
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.shared.qt import pyqtProperty

PLOT_BUCKETS = 400   # each plot gets at most about 800 points, however long the run


class DataLoggerViewModel(BaseViewModel):
    """Plots share one sample-number X range (req 17: linked X axes); -1 means auto-range."""

    changed = pyqtSignal()

    def __init__(self, logger: DataLoggerService, interactions: InteractionService, export_dir: Path,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._logger = logger
        self._interactions = interactions
        self._export_dir = export_dir
        self._series = DictListModel(["name", "unit", "samples", "points", "lastText"], self)
        self._recording = False
        self._field_count = 0
        self._sample_count = 0
        self._rate_text = "1.0"
        self._status_text = ""
        self._mode_text = ""
        self._zoom_start = -1.0
        self._zoom_end = -1.0
        logger.updated.connect(self._rebuild)
        self._rebuild()

    recording = qprop(bool, "_recording", changed)
    fieldCount = qprop(int, "_field_count", changed)
    sampleCount = qprop(int, "_sample_count", changed)
    rateText = qprop(str, "_rate_text", changed)
    statusText = qprop(str, "_status_text", changed)
    modeText = qprop(str, "_mode_text", changed)
    zoomStart = qprop(float, "_zoom_start", changed)
    zoomEnd = qprop(float, "_zoom_end", changed)

    @pyqtProperty(QObject, constant=True)
    def series(self) -> DictListModel:
        return self._series

    def _plot_data(self, s: Series) -> Tuple[List[float], List[float]]:
        """What the plots draw: the zoomed range (plus a point each side, so lines reach the edges), thinned."""
        lo, hi = 0, len(s.samples)
        if self._zoom_start >= 0:
            lo = max(0, bisect_left(s.samples, self._zoom_start) - 1)
            hi = min(hi, bisect_right(s.samples, self._zoom_end) + 1)
        return thin(s.samples[lo:hi], s.values[lo:hi], PLOT_BUCKETS)

    def _rebuild(self) -> None:
        rows = []
        for s in self._logger.series:
            last = f"{s.values[-1]:.3f} {s.unit}".strip() if s.values else "—"
            samples, points = self._plot_data(s)
            rows.append({"name": s.name, "unit": s.unit, "samples": samples, "points": points, "lastText": last})
        self._series.set_items(rows)
        logger = self._logger
        elapsed = logger.elapsed_s
        state = "Recording" if logger.recording else "Stopped"
        self._update(
            recording=logger.recording, field_count=len(logger.series), sample_count=logger.sample_count,
            rate_text=f"{logger.rate_s:g}",
            status_text=f"{state} · {logger.sample_count:,} samples · {int(elapsed // 60)}:{elapsed % 60:04.1f} elapsed",
            mode_text="station watch" if logger.mode == "watch" else "polling (rate outside 0.1–60 s watch range)",
        )

    @pyqtSlot()
    def toggleRecording(self) -> None:  # noqa: N802
        if self._logger.recording:
            self._logger.stop()
        elif not self._logger.series:
            self._interactions.toast("error", "Add fields to the logger first")
        else:
            self._logger.start()

    @pyqtSlot(str)
    def setRateText(self, text: str) -> None:  # noqa: N802
        try:
            rate = float(text.replace("s", "").strip())
        except ValueError:
            rate = -1
        if not RATE_MIN_S <= rate <= RATE_MAX_S:
            self._interactions.toast("error", f"Enter a sample rate between {RATE_MIN_S:g} and {RATE_MAX_S:g} seconds")
            self._rebuild()
            return
        self._logger.set_rate(rate)

    @pyqtSlot(int)
    def remove(self, row: int) -> None:
        name = self._series.get(row).get("name")
        if name:
            self._logger.untrack(name)

    @pyqtSlot()
    def clear(self) -> None:
        self.resetZoom()
        self._logger.clear()

    @pyqtSlot(float, float)
    def zoomTo(self, start: float, end: float) -> None:  # noqa: N802
        lo, hi = sorted((start, end))
        if hi - lo >= 1:  # ignore clicks and tiny drags
            self._update(zoom_start=lo, zoom_end=hi)
            self._rebuild()

    @pyqtSlot()
    def resetZoom(self) -> None:  # noqa: N802
        self._update(zoom_start=-1.0, zoom_end=-1.0)
        self._rebuild()

    @pyqtSlot()
    def exportCsv(self) -> None:  # noqa: N802
        path = self._export_dir / f"sirat_logger_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            self._logger.export_csv(path)
            self._interactions.toast("success", f"Exported {path}")
        except OSError as exc:
            self._interactions.toast("error", f"Couldn't export: {exc}")
