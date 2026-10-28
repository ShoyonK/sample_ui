"""Instruments page, temperature chamber card (req 29): live reading and trend, setpoint, wait for stable."""

from __future__ import annotations

from typing import Any, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.instruments.chamber import KIND, ChamberService
from sirat_ui.domains.instruments.instrument_viewmodel import (InstrumentViewModel, instrument_properties,
                                                              number)
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import qprop
from sirat_ui.state.station import StationState

FIELDS = ("target", "interval", "tolerance", "hold")


def problems(target: str, interval: str, tolerance: str, hold: str):
    errors = {}
    t, i, tol, h = number(target), number(interval), number(tolerance), number(hold)
    if t is None or not -40 <= t <= 150:
        errors["target"] = "Target must be between -40 and 150 °C"
    if i is None or not 0.5 <= i <= 60:
        errors["interval"] = "Update every 0.5 to 60 s"
    if tol is None or not 0 < tol <= 10:
        errors["tolerance"] = "Tolerance must be above 0 and at most 10 °C"
    if h is None or not 0 <= h <= 3600:
        errors["hold"] = "Hold time must be 0 to 3600 s"
    return errors


class ChamberViewModel(InstrumentViewModel):
    KIND = KIND
    changed = pyqtSignal()
    instrumentText, instrumentFound, instrumentConnected, errors, errorText = instrument_properties(changed)

    def __init__(self, service: ChamberService, bench: InstrumentBench, state: StationState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(bench, state, parent)
        self._service = service
        self._interactions = interactions
        self._target = "25"
        self._interval = f"{service.interval_s:g}"
        self._tolerance = "0.5"
        self._hold = "60"
        self._active = False
        service.changed.connect(lambda: self.changed.emit())
        self._errors = problems(self._target, self._interval, self._tolerance, self._hold)

    target = qprop(str, "_target", changed)
    interval = qprop(str, "_interval", changed)
    tolerance = qprop(str, "_tolerance", changed)
    hold = qprop(str, "_hold", changed)

    @pyqtProperty("QVariantList", notify=changed)
    def history(self) -> List[Any]:
        return list(self._service.history)

    @pyqtProperty(bool, notify=changed)
    def waiting(self) -> bool:
        return bool(self._service.wait_activity)

    @pyqtProperty(str, notify=changed)
    def waitText(self) -> str:  # noqa: N802
        return self._service.wait_text

    @pyqtProperty(str, notify=changed)
    def actualText(self) -> str:  # noqa: N802
        r = self._service.reading
        return f"{r.actual_c:.1f} °C" if r else "— °C"

    @pyqtProperty(str, notify=changed)
    def setpointText(self) -> str:  # noqa: N802
        r = self._service.reading
        return f"Setpoint {r.target_c:g} °C" if r else "No reading yet"

    @pyqtProperty(str, notify=changed)
    def trendText(self) -> str:  # noqa: N802
        """Stable, Heating or Cooling, the way the chamber's own panel says it."""
        r = self._service.reading
        if r is None:
            return ""
        if r.stable:
            return "Stable"
        return "Heating" if r.actual_c < r.target_c else "Cooling"

    @pyqtProperty(bool, notify=changed)
    def stable(self) -> bool:
        r = self._service.reading
        return bool(r and r.stable)

    @pyqtProperty(bool, notify=changed)
    def canSet(self) -> bool:  # noqa: N802
        return "target" not in self._errors and self._service.can("instruments.chamber.set_temp")

    @pyqtProperty(bool, notify=changed)
    def canWait(self) -> bool:  # noqa: N802
        return (not {"tolerance", "hold"} & set(self._errors) and not self._service.wait_activity
                and self._service.can("instruments.chamber.wait_stable"))

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name not in FIELDS:
            return
        self._set_field(name, value, lambda: problems(self._target, self._interval, self._tolerance, self._hold))
        if name == "interval" and "interval" not in self._errors and self._active:
            self._service.start_polling(number(value))

    @pyqtSlot(bool)
    def setActive(self, active: bool) -> None:  # noqa: N802
        """The page is showing: poll the chamber at the chosen interval; hidden: stop."""
        self._active = active
        if active:
            self._service.start_polling(number(self._interval) if "interval" not in self._errors else None)
        else:
            self._service.stop_polling()

    @pyqtSlot()
    def setTemperature(self) -> None:  # noqa: N802
        celsius = number(self._target)
        if self.canSet and celsius is not None:
            self._service.set_temperature(celsius).then(
                lambda _: self._interactions.toast("success", f"Chamber set to {celsius:g} °C"))

    @pyqtSlot()
    def waitForStable(self) -> None:  # noqa: N802
        tolerance, hold = number(self._tolerance), number(self._hold)
        if self.canWait and tolerance is not None and hold is not None:
            self._service.wait_stable(tolerance, hold)

    @pyqtSlot()
    def abortWait(self) -> None:  # noqa: N802
        self._service.abort_wait()


__all__: List[str] = ["ChamberViewModel"]
