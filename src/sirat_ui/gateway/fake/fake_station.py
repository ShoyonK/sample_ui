"""FakeStationGateway: a stateful, in-memory station that honours the API contract.

It enforces the same requires rules (via core.requires) and returns the same error codes as the
real service, so the UI can't depend on behaviour the real backend won't have.

Test knobs: auto_resolve/release(), fail_next(), time_out_next(), set_latency(), drop_dut(), emit_watch_tick(),
drop_instrument(), restart_station(), swallow_next(), duplicate_next(), calls, bench (the instruments' state,
gateway/fake/instruments.py), the memory and console knobs on `advanced` (gateway/fake/advanced.py), and test
outcomes on `station_tests`. The registers.* methods are in gateway/fake/registers.py.
"""

from __future__ import annotations

import itertools
import time
from datetime import datetime, timezone
from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from typing import Any, Callable, DefaultDict, Deque, Dict, List, Optional, Set, Tuple

from sirat_ui.core.observable import Event
from sirat_ui.core.ops import op_kind
from sirat_ui.core.prs import DISABLE, FALLBACK_SIGNALS, channel_problem
from sirat_ui.core.requires import check_requires
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.fake.advanced import AdvancedMethods, FakeAdvanced
from sirat_ui.gateway.fake.chip import CHIP_FAMILY, CHIP_PART, CHIP_REVISION, build_chip
from sirat_ui.gateway.fake.instruments import FakeBench
from sirat_ui.gateway.fake.register_memory import RegisterMemory
from sirat_ui.gateway.fake.registers import FakeRegisters, RegisterMethods
from sirat_ui.gateway.fake.sequencer import FakeActivity, FakeSequencer
from sirat_ui.gateway.port import CLIENT, PROTOCOL
from sirat_ui.gateway.fake.station_tests import FakeStationTests, StationTestMethods
from sirat_ui.gateway.scheduler import ManualScheduler, Scheduler
from sirat_ui.models.facts import Fault, InstrumentFacts, PositionFacts
from sirat_ui.models.registers import ChipInfo, PeripheralDef
from sirat_ui.models.radio import WifiPhyConfig
from sirat_ui.models.station import (CallLate, CapturePage, CaptureSpec, ChamberReading, ConnectResult,
                                     DutDisconnected, DutInfo, EcaSources, LoadPhyResult, LogLine, PhySpec,
                                     ProbeResult, PrsRoute, PrsSignalCatalog, RpcAddress, SiggenConfig, StationStatus,
                                     StatusChanged, WifiPhy)

RELEASE_ID = "fake-2026.10"
WORKSPACE_ADDRESS = ("localhost", 10001)  # what the fake's "workspace config" says for every position
POSITIONS = range(1, 5)


def _wifi_overrides(c: WifiPhyConfig) -> List[Tuple[str, str]]:
    """The TestInputs overrides load_wifi_phy applies for a config."""
    overrides = [("WIFI_MODE", c.mode), ("WIFI_STANDARD", c.standard), ("WIFI_CHANNEL", str(c.channel)),
                 ("WIFI_POWER_MODE", c.power_mode), ("WIFI_RATE", c.rate)]
    if c.tx_params:
        overrides += [("TX_PKT_LENGTH", str(c.tx_params.pkt_length)), ("TX_NUM_PKTS", str(c.tx_params.num_pkts)),
                      ("TX_MODE", c.tx_params.transmit_mode), ("TX_AGGR_ENABLE", str(c.tx_params.aggr_enable))]
    if c.advanced:
        overrides += [("PPDU_TYPE", c.advanced.ppdu_type), ("GI_LTF", c.advanced.gi_ltf),
                      ("DCM", str(int(c.advanced.dcm))), ("BANDWIDTH", c.advanced.bandwidth)]
    return overrides


@dataclass
class RecordedCall:
    """One call the fake received (for tests: calls, calls_to)."""
    method: str
    position: Optional[int]
    params: Dict[str, Any] = field(default_factory=dict)


class FakeStationGateway(AdvancedMethods, StationTestMethods, RegisterMethods):
    """See the module docstring. Construct with a ManualScheduler in tests (the default) or QtScheduler in the app."""

    def __init__(self, scheduler: Optional[Scheduler] = None, peripherals: Optional[List[PeripheralDef]] = None,
                 seed: int = 7, clock: Callable[[], float] = time.time) -> None:
        self.scheduler: Scheduler = scheduler or ManualScheduler()
        self.peripherals = peripherals or build_chip()
        self.memory = RegisterMemory(self.peripherals, seed)
        self.clock = clock
        self.events = Event()
        self.facts: Dict[int, PositionFacts] = {p: PositionFacts(p) for p in POSITIONS}
        self.calls: List[RecordedCall] = []
        self.auto_resolve = True
        self.default_latency_ms = 0
        self.drop_after_reads: Optional[int] = None
        self._latency: Dict[str, int] = {}
        self._held: Deque[Callable[[], None]] = deque()
        self._failures: Dict[str, Deque[ApiError]] = defaultdict(deque)
        self._timeouts: Dict[str, Deque[int]] = defaultdict(deque)   # method -> ms until the late result
        self._swallow: DefaultDict[type, int] = defaultdict(int)       # event type -> how many to lose
        self._duplicate: DefaultDict[type, int] = defaultdict(int)     # event type -> how many to send twice
        self._request_ids = itertools.count(1)
        self.connected_once: Set[int] = set()   # positions that were connected; dut.reconnect needs one
        self.bench = FakeBench(self.scheduler, self._emit_event,
                               lambda level, text: self._log(level, text, "instrument"),
                               self._emit_status, clock, lambda: self.chip.part)
        self.instruments: Dict[str, InstrumentFacts] = self.bench.instruments
        self._ids = itertools.count(1)
        self.rpc_timeout_s = 5.0
        self.chip = ChipInfo(CHIP_PART, CHIP_REVISION, CHIP_FAMILY)  # scenarios may swap in another family
        self.prs_routes: Dict[int, Dict[int, PrsRoute]] = defaultdict(dict)  # position -> channel -> route
        # where each position's DUT was reached; the workspace config unless connect overrode it
        self.addresses: Dict[int, Tuple[str, int]] = {p: WORKSPACE_ADDRESS for p in POSITIONS}
        self.unreachable_hosts = {"10.255.255.1"}  # test knob: these hosts never answer
        self.sequencer = FakeSequencer(self.scheduler, self._emit_event, self._execute_op, self._activity_done,
                                       lambda position: self.facts[position].dut_connected)
        self.advanced = FakeAdvanced(self._respond, self._log, self, self.peripherals, seed)
        self.fake_registers = FakeRegisters(self._respond, self._emit_event, self, self.scheduler, clock)
        self.station_tests = FakeStationTests(self._respond, self, self.scheduler, self._emit_event, self._emit_status)

    # ---------------------------------------------------------------- test knobs

    def set_latency(self, method: str, ms: int) -> None:
        self._latency[method] = ms

    def fail_next(self, method: str, code: ErrorCode, message: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        self._failures[method].append(ApiError(code, message or f"Simulated {code.value}", data))

    def time_out_next(self, method: str, late_ms: int = 1500) -> None:
        """The next call times out (data.still_running) but finishes late_ms later, announced by CallLate."""
        self._timeouts[method].append(late_ms)

    def drop_instrument(self, instrument_id: str) -> None:
        self.bench.drop(instrument_id)

    def release(self, count: Optional[int] = None) -> None:
        """Resolves held calls when auto_resolve is False."""
        n = len(self._held) if count is None else count
        for _ in range(min(n, len(self._held))):
            self._held.popleft()()

    def drop_dut(self, position: int, cause: str = "RPC connection lost", detected_by: str = "heartbeat") -> None:
        self._clear_dut(position)
        self._log("error", f"DUT {position} disconnected: {cause}")
        self._emit_event(DutDisconnected(position, cause, detected_by))
        self._emit_status()

    def emit_watch_tick(self, sub_id: Optional[str] = None) -> None:
        for watch in list(self.fake_registers.watches.values()):
            if sub_id is None or watch.sub_id == sub_id:
                self.fake_registers.tick(watch.sub_id)

    def swallow_next(self, event_type: type, count: int = 1) -> None:
        """The next `count` events of that type are lost, as on a dropped connection."""
        self._swallow[event_type] += count

    def duplicate_next(self, event_type: type, count: int = 1) -> None:
        """The next `count` events of that type arrive twice."""
        self._duplicate[event_type] += count

    def restart_station(self) -> None:
        """The service process restarts: every activity ends, and every DUT connection, watch and console session
        is gone, along with the bench setups, so dut.reconnect is refused until a full dut.connect. Each connected
        position reports dut.disconnected."""
        error = ApiError(ErrorCode.INTERNAL, "Station service restarted")
        self.sequencer.end_all(error)
        self.bench.end_all(error)
        self.station_tests.end_all(error)
        for position, facts in self.facts.items():
            was_connected = facts.dut_connected
            self._clear_dut(position)
            facts.activity, facts.fault = "idle", None
            if was_connected:
                self._emit_event(DutDisconnected(position, "Station service restarted", "station"))
        self.connected_once.clear()
        self._log("warning", "Station service restarted")
        self._emit_status()

    def _emit_event(self, event: Any) -> None:
        kind = type(event)
        if self._swallow[kind]:
            self._swallow[kind] -= 1
            return
        self.events.emit(event)
        if self._duplicate[kind]:
            self._duplicate[kind] -= 1
            self.events.emit(event)

    def calls_to(self, method: str) -> List[RecordedCall]:
        return [c for c in self.calls if c.method == method]

    # ---------------------------------------------------------------- plumbing

    def _respond(self, method: str, position: Optional[int], fn: Callable[[], Any], **params: Any) -> Call:
        self.calls.append(RecordedCall(method, position, params))
        call: Call = Call()
        request_id = next(self._request_ids)

        def checked() -> Any:
            if self._failures[method]:
                raise self._failures[method].popleft()
            if position is not None:
                missing = check_requires(method, self.facts.get(position), self.instruments.values())
                if missing:
                    raise ApiError(ErrorCode.WRONG_STATE, f"DUT {position} isn't ready for {method}",
                                   {"missing": missing})
            return fn()

        def finish_late() -> None:
            try:
                self._emit_event(CallLate(request_id, True, checked()))
            except ApiError as exc:
                self._emit_event(CallLate(request_id, False, error=exc))

        def run() -> None:
            if self._timeouts[method]:
                # API doc "Timeouts": reply timeout now, keep going, announce the outcome with call.late
                self.scheduler.later(self._timeouts[method].popleft(), finish_late)
                call.reject(ApiError(ErrorCode.TIMEOUT, f"{method} didn't answer in time",
                                     {"still_running": True, "request_id": request_id}))
                return
            try:
                call.resolve(checked())
            except ApiError as exc:
                call.reject(exc)

        if not self.auto_resolve:
            self._held.append(run)
        else:
            latency = self._latency.get(method, self.default_latency_ms)
            if latency > 0:
                self.scheduler.later(latency, run)
            else:
                run()
        return call

    def _instrument_call(self, method: str, kind: str, instrument_id: Optional[str],
                         fn: Callable[[InstrumentFacts], Any], **params: Any) -> Call:
        """Calls with an instrument `id` (or rf.paths, by kind): NOT_FOUND, then the requires check for it."""
        def run() -> Any:
            instrument = self.bench.require(kind, instrument_id)
            missing = check_requires(method, None, self.instruments.values(), instrument.id)
            if missing:
                raise ApiError(ErrorCode.WRONG_STATE, f"{instrument.id} isn't ready for {method}",
                               {"missing": missing})
            return fn(instrument)
        return self._respond(method, None, run, id=instrument_id, **params)

    def status_snapshot(self) -> StationStatus:
        return StationStatus(RELEASE_ID, [replace(f) for f in self.facts.values()],
                             [replace(i) for i in self.instruments.values()])

    def _emit_status(self) -> None:
        self._emit_event(StatusChanged(self.status_snapshot()))

    def _log(self, level: str, text: str, source: str = "station", position: Optional[int] = None) -> None:
        self._emit_event(LogLine(self.clock(), level, source, text, position))

    def _clear_dut(self, position: int) -> None:
        """Reset rules from the API doc: disconnect clears phy, watching and the RF path."""
        facts = self.facts[position]
        facts.dut_connected = False
        facts.phy = None
        facts.watching = False
        facts.rf_path = None
        self.advanced.end_sessions(position)
        self.fake_registers.drop_watches(position)

    # ---------------------------------------------------------------- sys

    def hello(self, client: str = CLIENT, protocol: int = PROTOCOL) -> Call:
        def run() -> Dict[str, Any]:
            now = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat()
            return {"release_id": RELEASE_ID, "protocol": PROTOCOL, "server_time": now}
        return self._respond("sys.hello", None, run, client=client, protocol=protocol)

    def status(self) -> Call:
        return self._respond("sys.status", None, self.status_snapshot)

    def subscribe(self, topics: List[str]) -> Call:
        return self._respond("sys.subscribe", None, lambda: None, topics=topics)

    def recover(self, position: int) -> Call:
        def run() -> None:
            self.facts[position].fault = None
            self.facts[position].activity = "idle"
            self._log("info", f"DUT {position} recovered: safe state applied, fault cleared", position=position)
            self._emit_status()
        return self._respond("sys.recover", None, run, pos=position)

    # ---------------------------------------------------------------- dut

    def connect_dut(self, position: int, config_type: str = "EFR32", config_file: str = "",
                    rpc: Optional[RpcAddress] = None) -> Call:
        def step(text: str) -> None:   # a progress line in the connect sheet's console
            self._log("info", text, "dut.connect", position)

        def run() -> ConnectResult:
            step(f"DUT {position}: bench setup ({config_type})")
            host, port = self._resolve_address(rpc)
            step(f"DUT {position}: RPC connect to {host}:{port}")
            self.addresses[position] = (host, port)
            self.facts[position].dut_connected = True
            self.connected_once.add(position)
            where = f" at {host}:{port}" if rpc else ""
            self._log("success", f"Connected to DUT {position} ({config_type}){where}")
            self._emit_status()
            return ConnectResult(self.chip, RpcAddress(host, port))
        return self._respond("dut.connect", position, run, config_type=config_type, config_file=config_file,
                             rpc=rpc)

    def reconnect_dut(self, position: int) -> Call[None]:
        def run() -> None:
            if position not in self.connected_once:
                raise ApiError(ErrorCode.NOT_FOUND, f"DUT {position} was never connected; connect it first")
            host, port = self.addresses[position]
            if host in self.unreachable_hosts:
                raise ApiError(ErrorCode.TIMEOUT, f"No answer from {host}:{port}")
            self.facts[position].dut_connected = True
            self._log("success", f"Reconnected RPC to DUT {position}")
            self._emit_status()
        return self._respond("dut.reconnect", position, run)

    def probe(self, position: int, rpc: Optional[RpcAddress], timeout_s: float) -> Call[ProbeResult]:
        def run() -> ProbeResult:
            try:
                host, port = self._resolve_address(rpc)
            except ApiError as exc:
                if exc.code != ErrorCode.TIMEOUT:
                    raise
                return ProbeResult(False, 0.0, f"{exc.message} within {timeout_s:g} s")
            return ProbeResult(True, 3.2, f"Reached the DUT {position} RPC server at {host}:{port}")
        return self._respond("dut.probe", None, run, pos=position, rpc=rpc, timeout_s=timeout_s)

    def _resolve_address(self, rpc: Optional[RpcAddress]) -> Tuple[str, int]:
        """No override: the workspace config. With one: validated, and unreachable hosts time out."""
        if rpc is None:
            return WORKSPACE_ADDRESS
        if not rpc.host or not str(rpc.host).strip():
            raise ApiError(ErrorCode.INVALID_PARAMS, "rpc.host must not be empty")
        if not 1 <= int(rpc.port) <= 65535:
            raise ApiError(ErrorCode.INVALID_PARAMS, "rpc.port must be between 1 and 65535")
        host = str(rpc.host).strip()
        if host in self.unreachable_hosts or host.endswith(".invalid"):
            raise ApiError(ErrorCode.TIMEOUT, f"No answer from {host}:{rpc.port}")
        return host, int(rpc.port)

    def disconnect_dut(self, position: int) -> Call:
        def run() -> None:
            self._clear_dut(position)
            self._log("info", f"Disconnected DUT {position}")
            self._emit_status()
        return self._respond("dut.disconnect", None, run, pos=position)

    def dut_info(self, position: int) -> Call:
        def run() -> DutInfo:
            chip = self.chip
            hw = {"PART_NUMBER": f"{chip.part}F1024IM40", "CHIPREVHW_CHIP_REV": chip.revision,
                  "CHIPREVHW_FAMILY_NAME": chip.family.lower(), "CHIPREVHW_PRODUCT_REV": 1,
                  "DEVINFO_NAME": chip.part[:9], "MEMINFO_FLASHSIZE": 1024, "MEMINFO_RAMSIZE": 256,
                  "UNIQUE_ID": 0x0123456789ABCDEF + position}
            host, port = self.addresses.get(position, WORKSPACE_ADDRESS)
            rta = {"host": host, "port": port, "timeout_s": self.rpc_timeout_s}
            app = {"name": "rail_test", "version": "2026.10.1", "build_time": "2026-10-20 09:14:03"}
            return DutInfo(chip.part, chip.revision, hw, rta, app)
        return self._respond("dut.info", position, run)

    def set_rpc_timeout(self, seconds: float) -> Call:
        def run() -> None:
            if not 1 <= seconds <= 300:
                raise ApiError(ErrorCode.INVALID_PARAMS, "timeout must be between 1 and 300 s")
            self.rpc_timeout_s = float(seconds)
        return self._respond("dut.set_rpc_timeout", None, run, seconds=seconds)

    def load_phy(self, position: int, phy: PhySpec) -> Call[LoadPhyResult]:
        def run() -> LoadPhyResult:
            overrides: List[Tuple[str, str]]
            if isinstance(phy, WifiPhy):
                if self.chip.family.upper() != "EVEREST":
                    raise ApiError(ErrorCode.INVALID_PARAMS,
                                   f"WiFi PHYs need an Everest-family DUT; this one is {self.chip.family.title()}")
                name, function, overrides = phy.config.phy_name, "load_wifi_phy", _wifi_overrides(phy.config)
            else:
                name, function, overrides = phy.name, "reset_and_download_lpw_phy", []
            self.facts[position].phy = name
            self._log("success", f"Loaded PHY {name} on DUT {position}")
            self._emit_status()
            return LoadPhyResult(name, function, tuple(overrides))
        return self._respond("dut.load_phy", position, run, phy=phy)

    # ---------------------------------------------------------------- rf (PRS)

    def prs_signals(self, position: int) -> Call[PrsSignalCatalog]:
        family = self.chip.family.lower()
        names = sorted({DISABLE} | {name for names in FALLBACK_SIGNALS.values() for name in names})
        return self._respond("rf.prs_signals", position, lambda: PrsSignalCatalog(
            family, f"dut_control_rta.series_six_lpw.{family}.controls.pti_prs_module", tuple(names)))

    def prs_route(self, position: int, route: PrsRoute) -> Call[None]:
        def run() -> None:
            problem = channel_problem(route.pin, route.channel)
            if problem:
                raise ApiError(ErrorCode.INVALID_PARAMS, problem)
            routes = self.prs_routes[position]
            if route.signal == DISABLE:
                routes.pop(route.channel, None)
                self._log("info", f"PRS channel {route.channel} disabled ({route.pin})")
            else:
                routes[route.channel] = route
                self._log("info", f"PRS {route.signal} routed to {route.pin} on channel {route.channel}")
        return self._respond("rf.prs_route", position, run, route=route)

    # ---------------------------------------------------------------- rf (RF switch, req 28)

    def rf_paths(self) -> Call[List[str]]:
        return self._instrument_call("rf.paths", "rf_switch", None, lambda _: list(self.bench.paths))

    def rf_connect(self, position: int, path: str) -> Call[None]:
        def run() -> None:
            self.bench.rf_connect(path)
            self.facts[position].rf_path = path
            self._log("info", f"RF switch connected {path} to DUT {position}")
            self._emit_status()
        return self._respond("rf.connect", position, run, path=path)

    def rf_disconnect(self, position: int) -> Call[None]:
        def run() -> None:
            self.facts[position].rf_path = None
            self._log("info", f"RF switch disconnected DUT {position}")
            self._emit_status()
        return self._respond("rf.disconnect", position, run)

    # ---------------------------------------------------------------- instruments (req 25-30)

    def list_instruments(self) -> Call[List[InstrumentFacts]]:
        return self._respond("instruments.list", None,
                             lambda: [replace(i) for i in self.instruments.values()])

    def connect_instrument(self, instrument_id: str, address: Optional[str] = None) -> Call[None]:
        """`address` is accepted but unused: the fake's instruments have no address to reach."""
        return self._respond("instruments.connect", None, lambda: self.bench.connect(instrument_id),
                             id=instrument_id, address=address)

    def siggen_get(self, instrument_id: str) -> Call[SiggenConfig]:
        return self._instrument_call("instruments.siggen.get", "signal_generator", instrument_id,
                                     lambda _: self.bench.siggen_get())

    def siggen_set(self, instrument_id: str, config: SiggenConfig) -> Call[None]:
        return self._instrument_call("instruments.siggen.set", "signal_generator", instrument_id,
                                     lambda _: self.bench.siggen_set(config), config=config)

    def siggen_waveforms(self, instrument_id: str, reload: bool = False) -> Call[List[str]]:
        return self._instrument_call("instruments.siggen.waveforms", "signal_generator", instrument_id,
                                     lambda _: self.bench.siggen_waveforms(reload), reload=reload)

    def siggen_trigger(self, instrument_id: str, mode: str) -> Call[None]:
        return self._instrument_call("instruments.siggen.trigger", "signal_generator", instrument_id,
                                     lambda _: self.bench.siggen_trigger(mode), mode=mode)

    def siggen_rf(self, instrument_id: str, on: bool) -> Call[None]:
        return self._instrument_call("instruments.siggen.rf", "signal_generator", instrument_id,
                                     lambda _: self.bench.siggen_rf(on), on=on)

    def chamber_read(self, instrument_id: str) -> Call[ChamberReading]:
        return self._instrument_call("instruments.chamber.read", "chamber", instrument_id,
                                     lambda _: self.bench.chamber_read())

    def chamber_set_temp(self, instrument_id: str, celsius: float) -> Call[None]:
        return self._instrument_call("instruments.chamber.set_temp", "chamber", instrument_id,
                                     lambda _: self.bench.chamber_set_temp(celsius), celsius=celsius)

    def chamber_wait_stable(self, instrument_id: str, tolerance_c: float = 0.5, hold_s: float = 60,
                            timeout_s: float = 3600) -> Call[str]:
        return self._instrument_call(
            "instruments.chamber.wait_stable", "chamber", instrument_id,
            lambda i: self.bench.chamber_wait_stable(i.id, tolerance_c, hold_s, timeout_s),
            tolerance_c=tolerance_c, hold_s=hold_s, timeout_s=timeout_s)

    def eca_sources(self, instrument_id: str) -> Call[EcaSources]:
        return self._instrument_call("instruments.eca.sources", "eca", instrument_id,
                                     lambda _: self.bench.eca_sources())

    def eca_capture(self, instrument_id: str, spec: CaptureSpec) -> Call[str]:
        return self._instrument_call("instruments.eca.capture", "eca", instrument_id,
                                     lambda i: self.bench.eca_capture(i.id, spec), spec=spec)

    def eca_result(self, capture_id: str, offset: int = 0, count: int = 65536) -> Call[CapturePage]:
        return self._respond("instruments.eca.result", None,
                             lambda: self.bench.eca_result(capture_id, offset, count),
                             capture_id=capture_id, offset=offset, count=count)

    # ---------------------------------------------------------------- automation

    def run_sequence(self, position: int, ops: List[Dict[str, Any]], stop_on_error: bool = True) -> Call:
        def run() -> str:
            activity_id = f"a{next(self._ids)}"
            self.facts[position].activity = "executing"
            self._emit_status()
            self.advanced.new_run_namespace(position)
            self.sequencer.start(FakeActivity(activity_id, position, list(ops), stop_on_error))
            return activity_id
        return self._respond("automation.seq.run", position, run, ops=list(ops))

    def abort_activity(self, activity_id: str) -> Call:
        def run() -> None:
            if not self.bench.abort(activity_id) and not self.station_tests.abort(activity_id):
                self.sequencer.abort(activity_id)
        return self._respond("activity.abort", None, run, activity_id=activity_id)

    def _op_instrument(self, kind: str, instrument_id: Optional[str]) -> None:
        instrument = self.bench.require(kind, instrument_id)
        if not instrument.connected:
            raise ApiError(ErrorCode.INSTRUMENT_ERROR, f"{instrument.id} isn't connected")

    def _activity_done(self, activity: FakeActivity) -> None:
        """API doc "Activities": a hardware error during an activity sets the position's fault (sys.recover
        clears it)."""
        facts = self.facts[activity.position]
        facts.activity = "idle"
        if activity.error is not None and activity.error.code == ErrorCode.HARDWARE_ERROR:
            error = activity.error
            facts.fault = Fault(str(error.data.get("cause") or error.code.value), error.message,
                                datetime.fromtimestamp(self.clock(), timezone.utc).isoformat())
            self._log("error", f"DUT {activity.position} fault: {activity.error.message}", position=activity.position)
        self._emit_status()

    def _execute_op(self, position: int, op: Dict[str, Any]) -> Any:
        kind = op_kind(op)
        if kind == "register_write":
            return self.memory.write(op["register"], int(op["value"]))
        if kind == "field_write":
            new_value = self.memory.field_insert(op["register"], op["field"], int(op["value"]))
            return self.memory.write(op["register"], new_value)
        if kind == "dut_reconnect":
            self.facts[position].dut_connected = True
        elif kind == "load_phy":
            self.facts[position].phy = op.get("phy_name")
        elif kind == "load_wifi_phy":
            self.facts[position].phy = (op.get("config") or {}).get("phy_name")
        elif kind == "prs_route":
            self.prs_routes[position][int(op["channel"])] = PrsRoute(op["signal"], op["pin"], int(op["channel"]))
        elif kind == "rf_switch":
            self._op_instrument("rf_switch", None)
            self.bench.rf_connect(str(op.get("path")))
            self.facts[position].rf_path = op.get("path")
        elif kind == "signal_generator":
            self._op_instrument("signal_generator", op.get("instrument_id"))
            self.bench.siggen_set(SiggenConfig(**op.get("config", {})))
        elif kind in ("custom_function", "dut_control_method"):
            return self.advanced.run_op(position, kind, op)
        elif kind == "sequence":
            raise ApiError(ErrorCode.INVALID_PARAMS, "sequence ops are expanded by the client, never sent")
        self._log("info", f"Executed {kind.replace('_', ' ')}")
        return None
