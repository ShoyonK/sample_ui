"""SignalGeneratorService (req 25): apply a configuration, trigger, RF on/off, load from the instrument, waveforms.

The settings persist in ~/.sirat/signal_generator.json (MHz, as the original wrote them); the wire takes Hz.
"""

from __future__ import annotations

from typing import List, Optional

from sirat_ui.core.instruments import siggen_action_name, siggen_op
from sirat_ui.core.observable import Event
from sirat_ui.domains.automation.recorder import ActionRecorder
from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.port import InstrumentsPort
from sirat_ui.models.actions import Action
from sirat_ui.models.instruments import SiggenSettings
from sirat_ui.models.station import SiggenConfig
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState
from sirat_ui.stores.json_store import JsonStore

KIND = "signal_generator"


def to_config(s: SiggenSettings) -> SiggenConfig:
    return SiggenConfig(s.sg_type, s.input_config_name, s.frequency_mhz * 1e6, s.power_dbm, dict(s.overrides))


def from_config(c: SiggenConfig) -> SiggenSettings:
    return SiggenSettings(c.sg_type, c.input_config_name, round(c.frequency_hz / 1e6, 6), c.power_dbm,
                          dict(c.overrides))


class SignalGeneratorService:
    def __init__(self, gateway: InstrumentsPort, state: StationState, bench: InstrumentBench, store: JsonStore,
                 actions: ActionRecorder, errors: ErrorPresenter, log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._bench = bench
        self._store = store
        self._actions = actions
        self._errors = errors
        self._log = log
        self.settings = SiggenSettings.from_json(store.load())
        self.waveforms: List[str] = []
        self.rf_on: Optional[bool] = None       # unknown until the GUI switches it
        self.trigger_mode = ""
        self.changed = Event()
        self._was_connected = False
        state.changed.connect(self._on_state)
        self._on_state()

    @property
    def instrument_id(self) -> str:
        return self._bench.instrument_id(KIND)

    def can(self, method: str) -> bool:
        return bool(self.instrument_id) and self._state.can(method, self.instrument_id)

    def _on_state(self, *_: object) -> None:
        found = self._bench.instrument(KIND)
        connected = bool(found and found.connected)
        if connected and not self._was_connected:
            self._was_connected = True
            self.load_waveforms()
        elif not connected and self._was_connected:
            self._was_connected = False
            self.rf_on, self.trigger_mode = None, ""
            self.changed.emit()

    def reload(self) -> None:
        """After a settings import or clear."""
        self.settings = SiggenSettings.from_json(self._store.load())
        self.changed.emit()

    def remember(self, settings: SiggenSettings) -> None:
        """Req 25 "Configuration persists across sessions"."""
        self.settings = settings
        self._store.save(settings.to_json())

    def load_waveforms(self, reload: bool = False) -> Call[List[str]]:
        def loaded(names: List[str]) -> None:
            self.waveforms = list(names)
            if reload:
                self._log.info(f"Signal generator waveforms reloaded ({len(names)} found)")
            self.changed.emit()

        return self._gateway.siggen_waveforms(self.instrument_id, reload).then(
            loaded, lambda e: self._errors.present(e, "Signal generator waveforms"))

    def apply(self, settings: SiggenSettings) -> Call[None]:
        def done(_: None) -> None:
            self.remember(settings)
            self._log.success(f"Signal generator configured: {settings.input_config_name}, "
                              f"{settings.frequency_mhz:g} MHz, {settings.power_dbm:g} dBm")
            self.changed.emit()

        return self._gateway.siggen_set(self.instrument_id, to_config(settings)).then(
            done, lambda e: self._errors.present(e, "Apply configuration"))

    def load_from_instrument(self) -> Call[SiggenConfig]:
        def loaded(config: SiggenConfig) -> None:
            self.remember(from_config(config))
            self._log.info(f"Loaded the configuration from {self.instrument_id}")
            self.changed.emit()

        return self._gateway.siggen_get(self.instrument_id).then(
            loaded, lambda e: self._errors.present(e, "Load from signal generator"))

    def trigger(self, mode: str) -> Call[None]:
        def done(_: None) -> None:
            self.trigger_mode = mode
            self.changed.emit()

        label = "Infinite trigger" if mode == "infinite" else "Single trigger"
        return self._gateway.siggen_trigger(self.instrument_id, mode).then(
            done, lambda e: self._errors.present(e, label))

    def set_rf(self, on: bool) -> Call[None]:
        def done(_: None) -> None:
            self.rf_on = on
            self._log.info(f"Signal generator RF {'on' if on else 'off'}")
            self.changed.emit()

        return self._gateway.siggen_rf(self.instrument_id, on).then(
            done, lambda e: self._errors.present(e, "RF ON" if on else "RF OFF"))

    def add_action(self, settings: SiggenSettings) -> Action:
        self.remember(settings)
        instrument_id = self.instrument_id or "siggen1"
        # Unchecked, like the seeded siggen action: Run checked shouldn't start the generator unless asked to.
        return self._actions.add(siggen_action_name(settings), [siggen_op(settings, instrument_id)], enabled=False)
