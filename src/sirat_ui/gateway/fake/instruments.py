"""The fake bench's instruments: signal generator, RF switch, temperature chamber and ECA (req 25-30).

FakeStationGateway owns one FakeBench and delegates the rf.* and instruments.* methods to it. The chamber ramps
towards its setpoint in scheduler time, and ECA captures are synthesized radio-burst waveforms, so the GUI has
something real to wait for, plot and measure.
"""

from __future__ import annotations

import base64
import itertools
import math
import random
from array import array
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sirat_ui.core.eca import MAX_SAMPLES
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.scheduler import Handle, Scheduler
from sirat_ui.models.facts import InstrumentFacts
from sirat_ui.models.station import (ActivityFinished, ActivityProgress, CaptureMeta, CapturePage, CaptureSpec,
                                     ChamberReading, EcaSources, EDGES, SiggenConfig)

WAVEFORM_FILES = ["BLE_1M", "BLE_2M", "BLE_LR_S2", "BLE_LR_S8", "IEEE802154_OQPSK", "GFSK_500K"]
SWITCH_PATHS = ["TX_PATH", "RX_PATH", "LOOPBACK", "ANT1", "ANT2"]
ECA_CHANNELS = ("PA_EN", "RX_EN", "PRS_CH0", "RF_ENV")
ECA_TRIGGERS = ("PA_EN", "RX_EN", "PRS_CH0", "EXT")

CHAMBER_RANGE_C = (-40.0, 150.0)
CHAMBER_RAMP_C_PER_S = 2.0
CAPTURE_STEPS = ("Arming", "Waiting for trigger", "Capturing", "Uploading")
CAPTURE_STEP_MS = 300

@dataclass
class _Activity:
    activity_id: str
    instrument_id: str
    aborted: bool = False
    handle: Optional[Handle] = None

@dataclass
class _Capture:
    meta: CaptureMeta
    samples: Dict[str, array] = field(default_factory=dict)

class FakeBench:
    def __init__(self, scheduler: Scheduler, emit: Callable[[Any], None], log: Callable[[str, str], None],
                 emit_status: Callable[[], None], clock: Callable[[], float], chip: Callable[[], str]) -> None:
        self._scheduler = scheduler
        self._emit = emit
        self._log = log
        self._emit_status = emit_status
        self._clock = clock
        self._chip = chip
        self.instruments: Dict[str, InstrumentFacts] = {i.id: i for i in (
            InstrumentFacts("siggen1", "signal_generator", True, "SMBV100B"),
            InstrumentFacts("switch1", "rf_switch", True, "RF switch matrix"),
            InstrumentFacts("chamber1", "chamber", True, "Espec SU-262"),
            InstrumentFacts("eca1", "eca", True, "ECA"),
        )}
        # signal generator
        self.waveform_files = list(WAVEFORM_FILES)       # test knob: what a reload would find
        self.waveforms = list(WAVEFORM_FILES)
        self.siggen = SiggenConfig(input_config_name="BLE_1M")
        self.rf_on = False
        self.trigger_mode = ""
        # RF switch
        self.paths = list(SWITCH_PATHS)
        # chamber
        self.chamber_actual = 23.0
        self.chamber_target = 23.0
        self._ramp: Optional[Handle] = None
        # ECA
        self.captures: Dict[str, _Capture] = {}
        self._activities: Dict[str, _Activity] = {}
        self._ids = itertools.count(1)

    # ---------------------------------------------------------------- shared

    def require(self, kind: str, instrument_id: Optional[str]) -> InstrumentFacts:
        """NOT_FOUND for an unknown id; the requires check (connected, idle) happens in the gateway."""
        if instrument_id is None:
            found = next((i for i in self.instruments.values() if i.kind == kind), None)
        else:
            found = self.instruments.get(instrument_id)
        if found is None or found.kind != kind:
            raise ApiError(ErrorCode.NOT_FOUND, f"No {kind.replace('_', ' ')} called {instrument_id}")
        return found

    def connect(self, instrument_id: str) -> None:
        if instrument_id not in self.instruments:
            raise ApiError(ErrorCode.NOT_FOUND, f"No instrument called {instrument_id}")
        self.instruments[instrument_id].connected = True
        self._log("success", f"Instrument {instrument_id} connected")
        self._emit_status()

    def drop(self, instrument_id: str) -> None:
        """An instrument drop ends its activity with instrument_error (API doc section 4)."""
        self.instruments[instrument_id].connected = False
        for activity in [a for a in self._activities.values() if a.instrument_id == instrument_id]:
            self._finish(activity, False, error=ApiError(ErrorCode.INSTRUMENT_ERROR, f"{instrument_id} disconnected"))
        self._log("error", f"Instrument {instrument_id} disconnected")
        self._emit_status()

    def _start(self, instrument_id: str, activity_name: str) -> _Activity:
        activity = _Activity(f"i{next(self._ids)}", instrument_id)
        self._activities[activity.activity_id] = activity
        self.instruments[instrument_id].activity = activity_name
        self._emit_status()
        return activity

    def _progress(self, activity: _Activity, step: int, total: int, message: str) -> None:
        self._emit(ActivityProgress(activity.activity_id, 0, step, total, message, instrument_id=activity.instrument_id))

    def _finish(self, activity: _Activity, ok: bool, result: Any = None, error: Optional[ApiError] = None) -> None:
        if self._activities.pop(activity.activity_id, None) is None:
            return
        if activity.handle:
            activity.handle.cancel()
        self.instruments[activity.instrument_id].activity = "idle"
        self._emit_status()
        self._emit(ActivityFinished(activity.activity_id, 0, ok, error=error, instrument_id=activity.instrument_id,
                                    result=result))

    def abort(self, activity_id: str) -> bool:
        """True when the id was one of the bench's activities."""
        activity = self._activities.get(activity_id)
        if activity is None:
            return False
        activity.aborted = True
        return True

    # ---------------------------------------------------------------- signal generator (req 25)

    def siggen_set(self, config: SiggenConfig) -> None:
        if config.input_config_name not in self.waveforms:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"Waveform '{config.input_config_name}' isn't loaded on the "
                                                     "signal generator")
        if not 0 < config.frequency_hz <= 6e9:
            raise ApiError(ErrorCode.INVALID_PARAMS, "frequency_hz must be between 0 and 6 GHz")
        if not -150 <= config.power_dbm <= 30:
            raise ApiError(ErrorCode.INVALID_PARAMS, "power_dbm must be between -150 and 30")
        self.siggen = SiggenConfig(config.sg_type, config.input_config_name, config.frequency_hz, config.power_dbm,
                                   dict(config.overrides))
        self._log("info", f"Signal generator loaded {config.input_config_name} at {config.frequency_hz / 1e6:g} MHz, "
                          f"{config.power_dbm:g} dBm")

    def siggen_get(self) -> SiggenConfig:
        s = self.siggen
        return SiggenConfig(s.sg_type, s.input_config_name, s.frequency_hz, s.power_dbm, dict(s.overrides))

    def siggen_waveforms(self, reload: bool) -> List[str]:
        if reload:
            self.waveforms = list(self.waveform_files)
            self._log("info", f"Signal generator rescanned its waveform files ({len(self.waveforms)} found)")
        return list(self.waveforms)

    def siggen_trigger(self, mode: str) -> None:
        if mode not in ("infinite", "single"):
            raise ApiError(ErrorCode.INVALID_PARAMS, "mode must be infinite or single")
        self.trigger_mode = mode
        self._log("info", f"Signal generator {mode} trigger")

    def siggen_rf(self, on: bool) -> None:
        self.rf_on = on
        self._log("info", f"Signal generator RF {'on' if on else 'off'}")

    # ---------------------------------------------------------------- RF switch (req 28)

    def rf_connect(self, path: str) -> None:
        if path not in self.paths:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"Unknown switch path '{path}'")

    # ---------------------------------------------------------------- temperature chamber (req 29)

    def chamber_read(self) -> ChamberReading:
        return ChamberReading(round(self.chamber_actual, 2), self.chamber_target,
                              abs(self.chamber_actual - self.chamber_target) <= 0.5)

    def chamber_set_temp(self, celsius: float) -> None:
        lo, hi = CHAMBER_RANGE_C
        if not lo <= celsius <= hi:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"The chamber's range is {lo:g} to {hi:g} °C")
        self.chamber_target = float(celsius)
        self._log("info", f"Chamber setpoint {celsius:g} °C")
        if self._ramp is None:
            self._ramp = self._scheduler.every(1000, self._chamber_step)

    def _chamber_step(self) -> None:
        delta = self.chamber_target - self.chamber_actual
        if abs(delta) <= CHAMBER_RAMP_C_PER_S:
            self.chamber_actual = self.chamber_target
            if self._ramp is not None:
                self._ramp.cancel()
                self._ramp = None
        else:
            self.chamber_actual += math.copysign(CHAMBER_RAMP_C_PER_S, delta)

    def chamber_wait_stable(self, instrument_id: str, tolerance_c: float, hold_s: float, timeout_s: float) -> str:
        if tolerance_c <= 0 or hold_s < 0 or timeout_s <= 0:
            raise ApiError(ErrorCode.INVALID_PARAMS, "tolerance_c and timeout_s must be positive, hold_s at least 0")
        activity = self._start(instrument_id, "waiting")
        state = {"elapsed": 0, "held": 0}
        total = max(1, int(math.ceil(hold_s)))

        def tick() -> None:
            if activity.aborted:
                self._finish(activity, False, error=ApiError(ErrorCode.ABORTED, "Aborted by user"))
                return
            state["elapsed"] += 1
            within = abs(self.chamber_actual - self.chamber_target) <= tolerance_c
            state["held"] = state["held"] + 1 if within else 0
            self._progress(activity, min(state["held"], total), total,
                           f"{self.chamber_actual:.1f} °C, target {self.chamber_target:g} °C, "
                           f"stable for {state['held']} of {total} s")
            if state["held"] >= hold_s:
                self._log("success", f"Chamber stable at {self.chamber_target:g} °C")
                self._finish(activity, True, result={"actual_c": round(self.chamber_actual, 2)})
            elif state["elapsed"] >= timeout_s:
                self._finish(activity, False, error=ApiError(
                    ErrorCode.TIMEOUT, f"The chamber didn't settle within {timeout_s:g} s"))

        activity.handle = self._scheduler.every(1000, tick)
        return activity.activity_id

    # ---------------------------------------------------------------- ECA (req 30)

    def eca_sources(self) -> EcaSources:
        return EcaSources(ECA_CHANNELS, ECA_TRIGGERS)

    def eca_capture(self, instrument_id: str, spec: CaptureSpec) -> str:
        unknown = [c for c in spec.channels if c not in ECA_CHANNELS]
        if not spec.channels or unknown:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"Unknown channels: {', '.join(unknown)}" if unknown
                           else "Pick at least one channel")
        if spec.trigger != "immediate" and spec.trigger not in ECA_TRIGGERS:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"Unknown trigger source '{spec.trigger}'")
        if spec.edge not in EDGES or not 0 <= spec.pretrigger_pct <= 90:
            raise ApiError(ErrorCode.INVALID_PARAMS, "edge or pretrigger_pct is out of range")
        count = int(round(spec.sample_rate_hz * spec.duration_s))
        if spec.sample_rate_hz <= 0 or spec.duration_s <= 0 or not 2 <= count <= MAX_SAMPLES:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"A capture holds 2 to {MAX_SAMPLES:,} samples; "
                                                     f"this one would be {count:,}")
        activity = self._start(instrument_id, "capturing")
        state = {"step": 0}

        def tick() -> None:
            if activity.aborted:
                self._finish(activity, False, error=ApiError(ErrorCode.ABORTED, "Aborted by user"))
                return
            if state["step"] < len(CAPTURE_STEPS):
                state["step"] += 1
                self._progress(activity, state["step"], len(CAPTURE_STEPS), CAPTURE_STEPS[state["step"] - 1])
                return
            capture_id = f"c{next(self._ids)}"
            meta = CaptureMeta(spec, self._clock(), count, self._chip(), 0)
            self.captures[capture_id] = _Capture(meta, synthesize(spec, count))
            self._log("success", f"ECA captured {count:,} samples on {', '.join(spec.channels)}")
            self._finish(activity, True, result={"capture_id": capture_id})

        activity.handle = self._scheduler.every(CAPTURE_STEP_MS, tick)
        return activity.activity_id

    def eca_result(self, capture_id: str, offset: int, count: int) -> CapturePage:
        capture = self.captures.get(capture_id)
        if capture is None:
            raise ApiError(ErrorCode.NOT_FOUND, f"Capture {capture_id} is gone (captures are kept for an hour)")
        total = capture.meta.sample_count
        if offset < 0 or count <= 0:
            raise ApiError(ErrorCode.INVALID_PARAMS, "offset must be at least 0 and count positive")
        end = min(total, offset + count)
        channels = {name: base64.b64encode(samples[offset:end].tobytes()).decode("ascii")
                    for name, samples in capture.samples.items()}
        more = end < total
        if not more:
            self.captures.pop(capture_id)  # kept until the last page is read
        return CapturePage(capture.meta, offset, end - offset, channels, more)

# ---- waveform synthesis -----------------------------------------------------------------------------------

BURST_PERIOD_S = 1.25e-3     # a TX burst every 1.25 ms (a BLE connection-event cadence)
TX_S = 0.376e-3              # a 47-byte LE 1M packet on air
IFS_S = 0.150e-3
RX_S = 0.300e-3
HIGH = 3300                  # digital high, in mV

def synthesize(spec: CaptureSpec, count: int) -> Dict[str, array]:
    """Each channel's samples (int16, mV): TX bursts start at the trigger point and repeat every period."""
    rng = random.Random(count)
    pre = spec.duration_s * spec.pretrigger_pct / 100
    out: Dict[str, array] = {}
    for name in spec.channels:
        samples = array("h")
        for i in range(count):
            t = i / spec.sample_rate_hz - pre
            phase = t % BURST_PERIOD_S if t >= 0 else -1.0
            tx = 0 <= phase < TX_S
            rx = TX_S + IFS_S <= phase < TX_S + IFS_S + RX_S
            if name == "PA_EN":
                value = HIGH if tx else 0
            elif name == "RX_EN":
                value = HIGH if rx else 0
            elif name == "PRS_CH0":  # FRAMEDET: a short pulse 40 µs into each receive window
                value = HIGH if rx and phase - TX_S - IFS_S < 48e-6 and phase - TX_S - IFS_S >= 40e-6 else 0
            else:  # RF_ENV: the PA envelope with a 10 µs ramp, plus noise
                ramp = min(1.0, phase / 10e-6, (TX_S - phase) / 10e-6) if tx else 0.0
                value = int(1800 * ramp + rng.gauss(40, 12))
            samples.append(max(-32768, min(32767, int(value))))
        out[name] = samples
    return out
