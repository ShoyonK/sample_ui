"""Instruments page, signal generator card (req 25): the configuration, Apply, triggers, RF, waveforms, actions."""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.instruments import format_overrides, parse_overrides, siggen_code, siggen_problems
from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.instruments.instrument_viewmodel import (InstrumentViewModel, instrument_properties,
                                                              number)
from sirat_ui.domains.instruments.siggen import KIND, SignalGeneratorService
from sirat_ui.models.instruments import SiggenSettings
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import qprop
from sirat_ui.state.station import StationState

FIELDS = ("sgType", "frequency", "power", "overrides")


class SignalGeneratorViewModel(InstrumentViewModel):
    KIND = KIND
    changed = pyqtSignal()
    instrumentText, instrumentFound, instrumentConnected, errors, errorText = instrument_properties(changed)

    def __init__(self, service: SignalGeneratorService, bench: InstrumentBench, state: StationState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(bench, state, parent)
        self._service = service
        self._interactions = interactions
        self._sgType = ""
        self._frequency = ""
        self._power = ""
        self._overrides = ""
        self._waveform = ""
        self._busy = False
        self._status = ""
        self._status_level = "mute"
        service.changed.connect(self._load)
        self._load()

    sgType = qprop(str, "_sgType", changed)
    frequency = qprop(str, "_frequency", changed)
    power = qprop(str, "_power", changed)
    overrides = qprop(str, "_overrides", changed)
    busy = qprop(bool, "_busy", changed)
    statusText = qprop(str, "_status", changed)
    statusLevel = qprop(str, "_status_level", changed)

    @pyqtProperty("QStringList", notify=changed)
    def waveforms(self) -> List[str]:
        names = list(self._service.waveforms)
        return names if not self._waveform or self._waveform in names else names + [self._waveform]

    @pyqtProperty(int, notify=changed)
    def waveformIndex(self) -> int:  # noqa: N802
        names = self.waveforms
        return names.index(self._waveform) if self._waveform in names else -1

    @pyqtProperty(bool, notify=changed)
    def waveformMissing(self) -> bool:  # noqa: N802
        """The saved waveform isn't one the instrument has loaded (Reload waveforms may find it)."""
        return bool(self._service.waveforms) and self._waveform not in self._service.waveforms

    @pyqtProperty(bool, notify=changed)
    def canApply(self) -> bool:  # noqa: N802
        return (not self._errors and not self._busy and bool(self._waveform)
                and self._service.can("instruments.siggen.set"))

    @pyqtProperty(bool, notify=changed)
    def canControl(self) -> bool:  # noqa: N802
        return not self._busy and self._service.can("instruments.siggen.trigger")

    @pyqtProperty(str, notify=changed)
    def rfState(self) -> str:  # noqa: N802
        """"on", "off" or "" (unknown: the GUI hasn't switched it since connecting)."""
        rf = self._service.rf_on
        return "" if rf is None else ("on" if rf else "off")

    @pyqtProperty(str, notify=changed)
    def triggerText(self) -> str:  # noqa: N802
        mode = self._service.trigger_mode
        return {"infinite": "Infinite trigger running", "single": "Single trigger sent"}.get(mode, "Not triggered")

    def _load(self) -> None:
        s = self._service.settings
        self._sgType, self._frequency, self._power = s.sg_type, f"{s.frequency_mhz:g}", f"{s.power_dbm:g}"
        self._overrides, self._waveform = format_overrides(s.overrides), s.input_config_name
        self._validate()

    def _validate(self) -> None:
        self._errors = siggen_problems(self._sgType, self._frequency, self._power, self._overrides)
        self.changed.emit()

    def _settings(self) -> SiggenSettings:
        freq, power = number(self._frequency), number(self._power)
        assert freq is not None and power is not None  # only called without errors
        return SiggenSettings(self._sgType.strip(), self._waveform, freq, power, parse_overrides(self._overrides)[0])

    def _status_line(self, text: str, level: str) -> None:
        self._update(status=text, status_level=level, busy=False)

    # ---- editing ------------------------------------------------------------------------------------------

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name in FIELDS:
            setattr(self, "_" + name, value)
            self._validate()
            if not self._errors:
                self._service.remember(self._settings())

    @pyqtSlot(int)
    def setWaveform(self, index: int) -> None:  # noqa: N802
        names = self.waveforms
        if 0 <= index < len(names):
            self._waveform = names[index]
            self._validate()
            if not self._errors:
                self._service.remember(self._settings())

    # ---- instrument -----------------------------------------------------------------------------------------

    @pyqtSlot()
    def apply(self) -> None:
        if not self.canApply:
            return
        settings = self._settings()
        self._update(busy=True)
        self._service.apply(settings).then(
            lambda _: self._status_line("Configuration applied", "ok"),
            lambda e: self._status_line(f"Apply failed: {e.message}", "danger"))

    @pyqtSlot()
    def loadFromInstrument(self) -> None:  # noqa: N802
        if not self._service.can("instruments.siggen.get"):
            return
        self._service.load_from_instrument().then(
            lambda _: self._status_line(f"Loaded from {self._service.instrument_id}", "ok"))

    @pyqtSlot()
    def reloadWaveforms(self) -> None:  # noqa: N802
        if self._service.can("instruments.siggen.waveforms"):
            self._service.load_waveforms(reload=True).then(
                lambda names: self._status_line(f"{len(names)} waveforms found", "mute"))

    @pyqtSlot(str)
    def trigger(self, mode: str) -> None:
        if mode in ("infinite", "single") and self.canControl:
            self._service.trigger(mode)

    @pyqtSlot(bool)
    def setRf(self, on: bool) -> None:  # noqa: N802
        if self.canControl:
            self._service.set_rf(on)

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if self._errors or not self._waveform:
            return
        action = self._service.add_action(self._settings())
        self._interactions.toast("success", f"Added {action.name} to Actions")

    @pyqtSlot()
    def showCode(self) -> None:  # noqa: N802
        if not self._errors:
            self._interactions.show_code("Signal generator code",
                                         siggen_code(self._settings(), self._service.instrument_id or "siggen1"))
