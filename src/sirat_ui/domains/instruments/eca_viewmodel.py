"""Instruments page, ECA capture card (req 30): configure, start, plot with zoom and markers, measure, save CSV."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.eca import MAX_SAMPLES, decimate, format_frequency, format_ms, measure
from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.instruments.eca import KIND, EcaService
from sirat_ui.domains.instruments.instrument_viewmodel import (InstrumentViewModel, instrument_properties,
                                                              number)
from sirat_ui.models.station import CaptureSpec, EDGES
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import DictListModel, qprop
from sirat_ui.state.station import StationState

FIELDS = ("rate", "duration", "pretrigger", "markerA", "markerB")
EDGE_LABELS = ["Rising", "Falling", "Either"]
SERIES_COLORS = ["info", "ok", "warn", "danger"]   # Theme tone names, cycled per channel

def problems(rate: str, duration: str, pretrigger: str, marker_a: str, marker_b: str) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    r, d, p = number(rate), number(duration), number(pretrigger)
    if r is None or not 0 < r <= 100:
        errors["rate"] = "Sample rate must be above 0 and at most 100 MHz"
    if d is None or not 0 < d <= 10_000:
        errors["duration"] = "Duration must be above 0 and at most 10 000 ms"
    if p is None or not 0 <= p <= 90 or not p.is_integer():
        errors["pretrigger"] = "Pre-trigger must be a whole number from 0 to 90 %"
    if r is not None and d is not None and "rate" not in errors and "duration" not in errors:
        count = int(round(r * 1e6 * d * 1e-3))
        if not 2 <= count <= MAX_SAMPLES:
            errors["duration"] = f"That's {count:,} samples per channel; a capture holds 2 to {MAX_SAMPLES:,}"
    for key, text in (("markerA", marker_a), ("markerB", marker_b)):
        if text.strip() and number(text) is None:
            errors[key] = "A time in ms"
    return errors

class EcaViewModel(InstrumentViewModel):
    KIND = KIND
    changed = pyqtSignal()
    instrumentText, instrumentFound, instrumentConnected, errors, errorText = instrument_properties(changed)

    def __init__(self, service: EcaService, bench: InstrumentBench, state: StationState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(bench, state, parent)
        self._service = service
        self._interactions = interactions
        self._rate, self._duration, self._pretrigger = "1", "5", "10"
        self._markerA = self._markerB = ""
        self._checked: Dict[str, bool] = {}
        self._trigger = "immediate"
        self._edge = "rising"
        self._window: Optional[Tuple[float, float]] = None
        self._shown_capture: Any = None
        self._channels = DictListModel(["name", "checked"], self)
        self._plots = DictListModel(["name", "xs", "ys", "tone"], self)
        self._measurements = DictListModel(["channel", "range", "mean", "edges", "frequency", "highTime",
                                            "firstRise"], self)
        self._errors = problems(self._rate, self._duration, self._pretrigger, "", "")
        service.changed.connect(self._refresh)
        self._refresh()

    @pyqtProperty(QObject, constant=True)
    def channels(self) -> QObject:
        return self._channels

    @pyqtProperty(QObject, constant=True)
    def plots(self) -> QObject:
        return self._plots

    @pyqtProperty(QObject, constant=True)
    def measurements(self) -> QObject:
        return self._measurements

    @pyqtProperty("QStringList", constant=True)
    def edges(self) -> List[str]:
        return EDGE_LABELS

    @pyqtProperty(int, notify=changed)
    def edgeIndex(self) -> int:  # noqa: N802
        return EDGES.index(self._edge)

    rate = qprop(str, "_rate", changed)
    duration = qprop(str, "_duration", changed)
    pretrigger = qprop(str, "_pretrigger", changed)
    markerA = qprop(str, "_markerA", changed)
    markerB = qprop(str, "_markerB", changed)

    @pyqtProperty(bool, notify=changed)
    def busy(self) -> bool:
        return self._service.busy

    @pyqtProperty(bool, notify=changed)
    def capturing(self) -> bool:
        return bool(self._service.activity)

    @pyqtProperty(str, notify=changed)
    def progressText(self) -> str:  # noqa: N802
        return self._service.progress_text

    @pyqtProperty(bool, notify=changed)
    def hasCapture(self) -> bool:  # noqa: N802
        return self._service.capture is not None

    @pyqtProperty("QStringList", notify=changed)
    def triggers(self) -> List[str]:
        sources = self._service.sources
        return ["immediate"] + (list(sources.triggers) if sources else [])

    @pyqtProperty(int, notify=changed)
    def triggerIndex(self) -> int:  # noqa: N802
        names = self.triggers
        return names.index(self._trigger) if self._trigger in names else 0

    @pyqtProperty(str, notify=changed)
    def samplesText(self) -> str:  # noqa: N802
        r, d = number(self._rate), number(self._duration)
        if r is None or d is None or "rate" in self._errors:
            return ""
        return f"{int(round(r * 1e6 * d * 1e-3)):,} samples per channel"

    @pyqtProperty(bool, notify=changed)
    def canCapture(self) -> bool:  # noqa: N802
        spec_errors = {"rate", "duration", "pretrigger"} & set(self._errors)
        return (not spec_errors and any(self._checked.values()) and not self._service.busy
                and self._service.can("instruments.eca.capture"))

    @pyqtProperty("QVariantList", notify=changed)
    def markers(self) -> List[float]:
        """Vertical lines on every plot: the trigger point, then markers A and B when set."""
        capture = self._service.capture
        lines = [capture.trigger_ms] if capture else []
        return lines + [v for v in (number(self._markerA), number(self._markerB)) if v is not None]

    @pyqtProperty(str, notify=changed)
    def markerText(self) -> str:  # noqa: N802
        a, b = number(self._markerA), number(self._markerB)
        if a is None or b is None or a == b:
            return "Set markers A and B to measure the time between them"
        delta = abs(b - a)
        return f"B − A = {format_ms(delta)} ({format_frequency(1e3 / delta)})"

    @pyqtProperty(float, notify=changed)
    def xMin(self) -> float:  # noqa: N802
        return self._window[0] if self._window else -1.0

    @pyqtProperty(float, notify=changed)
    def xMax(self) -> float:  # noqa: N802
        return self._window[1] if self._window else -1.0

    # ---- refresh ------------------------------------------------------------------------------------------

    def _refresh(self) -> None:
        sources = self._service.sources
        names = list(sources.channels) if sources else []
        if names and not self._checked:
            self._checked = {n: i < 2 for i, n in enumerate(names)}  # the first two, to start
        self._channels.set_items([{"name": n, "checked": self._checked.get(n, False)} for n in names])
        if self._service.capture is not self._shown_capture:
            self._shown_capture = self._service.capture
            self._window = None
            self._replot()
            self._remeasure()
        self.changed.emit()

    def _replot(self) -> None:
        capture = self._service.capture
        if capture is None:
            self._plots.set_items([])
            return
        rows = []
        for i, (name, values) in enumerate(capture.channels.items()):
            xs, ys = decimate(values, capture.rate, window=self._window)
            rows.append({"name": name, "xs": xs, "ys": ys, "tone": SERIES_COLORS[i % len(SERIES_COLORS)]})
        self._plots.set_items(rows)

    def _remeasure(self) -> None:
        capture = self._service.capture
        rows = []
        if capture is None:
            self._measurements.set_items([])
            return
        for name, values in capture.channels.items():
            m = measure(name, values, capture.rate)
            rows.append({"channel": name, "range": f"{m.minimum} to {m.maximum} mV", "mean": f"{m.mean:.0f} mV",
                         "edges": str(m.rising_edges), "frequency": format_frequency(m.frequency_hz),
                         "highTime": format_ms(m.high_time_us / 1e3) if m.high_time_us is not None else "—",
                         "firstRise": format_ms(m.first_rise_ms) if m.first_rise_ms is not None else "—"})
        self._measurements.set_items(rows)

    # ---- configuration --------------------------------------------------------------------------------------

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name in FIELDS:
            self._set_field(name, value, lambda: problems(self._rate, self._duration, self._pretrigger,
                                                          self._markerA, self._markerB))

    @pyqtSlot(int)
    def toggleChannel(self, row: int) -> None:  # noqa: N802
        if 0 <= row < self._channels.count:
            name = self._channels.get(row)["name"]
            self._checked[name] = not self._checked.get(name, False)
            self._refresh()

    @pyqtSlot(int)
    def setTrigger(self, index: int) -> None:  # noqa: N802
        names = self.triggers
        if 0 <= index < len(names):
            self._update(trigger=names[index])

    @pyqtSlot(int)
    def setEdge(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(EDGES):
            self._update(edge=EDGES[index])

    def spec(self) -> CaptureSpec:
        r, d, p = number(self._rate), number(self._duration), number(self._pretrigger)
        assert r is not None and d is not None and p is not None
        channels = tuple(n for n in (self._service.sources.channels if self._service.sources else ())
                         if self._checked.get(n))
        return CaptureSpec(channels, self._trigger, self._edge, r * 1e6, d * 1e-3, int(p))

    # ---- capture -----------------------------------------------------------------------------------------------

    @pyqtSlot()
    def capture(self) -> None:
        if self.canCapture:
            self._service.start(self.spec())

    @pyqtSlot()
    def abort(self) -> None:
        self._service.abort()

    @pyqtSlot(float, float)
    def zoom(self, start: float, end: float) -> None:
        lo, hi = sorted((start, end))
        if hi - lo > 0:
            self._window = (max(0.0, lo), hi)
            self._replot()
            self.changed.emit()

    @pyqtSlot()
    def resetZoom(self) -> None:  # noqa: N802
        self._window = None
        self._replot()
        self.changed.emit()

    @pyqtSlot()
    def saveCsv(self) -> None:  # noqa: N802
        capture = self._service.capture
        if capture is None:
            return
        suggested = f"eca_capture_{'_'.join(capture.channels).lower()}.csv"

        def chosen(path: Optional[str]) -> None:
            if path:
                self._service.save_csv(Path(path))
                self._interactions.toast("success", f"Saved {Path(path).name}")

        self._interactions.choose_save_file("Save ECA capture", suggested, "CSV files (*.csv)").then(chosen)

__all__: List[str] = ["EcaViewModel"]
