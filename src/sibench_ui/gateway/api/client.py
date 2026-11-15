"""ApiStationGateway: the StationGateway that talks to a station service over TCP (docs/STATION_API.md).

Each method sends one request for the protocol method it's bound to (gateway/wire/bindings.py) and decodes the
reply into the frontend's models, so services can't tell it from FakeStationGateway. Events arrive as
GatewayEvents on `events`.

The link itself (connecting in the background, holding calls made meanwhile, reconnecting with backoff, the
heartbeat, subscribing again, spotting lost events) is station_client.Link, which any tool can use. What's
the GUI's own is here:
- If the link drops, every connected DUT position gets a DutDisconnected (the app shows its usual recovery), and
  once it's back (or when events were lost) sys.status is fetched again, so the app catches up.
- A call.late result is decoded with the method of the call that timed out.
- Link changes are logged as LogLines.

Callbacks and events run wherever `post` runs them: the GUI thread in the app (app/qt_post.py).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set

from station_client.link import (CLOSED, CONNECTING, HEARTBEAT_S, HEARTBEAT_TIMEOUT_MS, IDLE, LOST, OPEN,
                                 RETRY_FIRST_S, RETRY_MAX_S, UNREACHABLE, WAITING, Link, LinkChange)
from station_client.timers import Post
from station_protocol import jsonrpc
from station_protocol.method import unwrap
from sibench_ui.core.observable import Event
from sibench_ui.gateway.call import Call
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.port import CLIENT, PROTOCOL
from sibench_ui.gateway.scheduler import Scheduler
from sibench_ui.gateway.wire.bindings import BY_ATTR, Binding
from sibench_ui.gateway.wire.codec import CodecError, decode, encode
from sibench_ui.gateway.wire.events import decode_event
from sibench_ui.models.facts import InstrumentFacts
from sibench_ui.models.registers import PeripheralDef
from sibench_ui.models.station import (ApiTree, CallLate, CapturePage, CaptureSpec, ChamberReading, ConnectResult,
                                     DutDisconnected, DutInfo, EcaSources, ExecResult, InvokeRes, LoadPhyResult,
                                     LogLine, MemoryBlock, MemoryWriteRes, NameInfo, PhySpec, ProbeResult, PrsRoute,
                                     PrsSignalCatalog, ReadManyItem, RpcAddress, SiggenConfig, StationStatus,
                                     StationTest, StatusChanged, WriteResult)

DEFAULT_TIMEOUT_S = 5.0

__all__ = ["ApiStationGateway", "IDLE", "CONNECTING", "OPEN", "WAITING", "CLOSED"]


class ApiStationGateway:
    """See the module docstring. start() (or open(), which blocks) brings the link up; close() ends it for good."""

    def __init__(self, host: str, port: int, scheduler: Scheduler, post: Post, clock: Any = time.time,
                 heartbeat_s: float = HEARTBEAT_S, heartbeat_timeout_ms: int = HEARTBEAT_TIMEOUT_MS,
                 retry_first_s: float = RETRY_FIRST_S, retry_max_s: float = RETRY_MAX_S) -> None:
        self.events = Event()
        self.timeout_s = DEFAULT_TIMEOUT_S
        self._clock = clock
        self._timed_out: Dict[Any, Binding] = {}      # request id of a timed-out call -> its method
        self._connected: Set[int] = set()            # DUT positions the last status showed connected
        self._link = Link(host, port, scheduler, post, CLIENT, self._on_notification, self._on_change,
                          protocol=PROTOCOL, heartbeat_s=heartbeat_s, heartbeat_timeout_ms=heartbeat_timeout_ms,
                          retry_first_s=retry_first_s, retry_max_s=retry_max_s)

    @property
    def host(self) -> str:
        return self._link.host

    @property
    def port(self) -> int:
        return self._link.port

    @property
    def address(self) -> str:
        return self._link.address

    @property
    def state(self) -> str:
        """idle, connecting, open, waiting (to retry) or closed."""
        return self._link.state

    @property
    def reason(self) -> str:
        """Why the link isn't open."""
        return self._link.reason

    # ---- the link ----------------------------------------------------------------------------------------

    def open(self) -> None:
        """Connects now, blocking. Raises ApiError(INTERNAL) when the station can't be reached; the client then
        keeps retrying in the background."""
        self._link.open()

    def start(self) -> None:
        """Connects in the background; calls made meanwhile wait for the connection."""
        self._link.start()

    def close(self) -> None:
        """Ends the link for good: no more retries; pending and held calls fail."""
        self._link.close()

    def _on_change(self, change: LinkChange) -> None:
        if change.kind == UNREACHABLE:
            self._log("error", f"{change.reason}. Retrying in the background.")
        elif change.kind == LOST:
            self._log("error", f"{change.reason}. Reconnecting…")
            for position in sorted(self._connected):
                self.events.emit(DutDisconnected(position, change.reason, "station connection"))
            self._connected.clear()
        else:
            self._timed_out.clear()   # request ids start again on a new connection
            if change.reconnect:
                self._log("success", f"Reconnected to the station at {self.address}")
                self._refetch_status()

    def _log(self, level: str, text: str) -> None:
        self.events.emit(LogLine(self._clock(), level, "gateway", text))

    def _refetch_status(self) -> None:
        self.status().then(lambda status: self.events.emit(StatusChanged(status)))

    # ---- requests ----------------------------------------------------------------------------------------

    def _call(self, attr: str, *args: Any) -> Call:
        method = BY_ATTR[attr]
        params = {p.wire: encode(a) for p, a in zip(method.method.params, args)}
        call: Call = Call()

        def done(raw: Any, error: Optional[ApiError]) -> None:
            if error is None:
                call.resolve(raw)
            else:
                self._note_timeout(method, error)
                call.reject(error)
        if attr == "subscribe":
            self._link.subscribe(params["topics"], int(self.timeout_s * 1000), done)
        else:
            self._link.request(method.method.wire, params, int(self.timeout_s * 1000), done)
        return call.map(lambda raw: self._decode_result(method, raw))

    @staticmethod
    def _decode_result(method: Binding, raw: Any) -> Any:
        if method.result is None:
            return None
        try:
            return decode(method.result, unwrap(method.method, raw), method.method.wrap)
        except CodecError as exc:
            raise ApiError(ErrorCode.INTERNAL,
                           f"The station's reply to {method.method.wire} doesn't fit: {exc}") from None

    def _note_timeout(self, method: Binding, error: ApiError) -> None:
        if error.code == ErrorCode.TIMEOUT and error.data.get("still_running") and "request_id" in error.data:
            self._timed_out[error.data["request_id"]] = method

    # ---- events ------------------------------------------------------------------------------------------

    def _on_notification(self, note: jsonrpc.Notification, gap: bool) -> None:
        try:
            event = decode_event(note.method, note.data)
        except KeyError:
            return   # an event this client doesn't know (a newer station): ignore it
        except CodecError as exc:
            self._log("warning", f"Ignored a {note.method} event: {exc}")
            return
        if isinstance(event, CallLate):
            event = self._late(event)
        if isinstance(event, StatusChanged):
            self._remember(event.status)
        self.events.emit(event)
        if gap:   # events were lost: the status may be stale
            self._refetch_status()

    def _late(self, event: CallLate) -> CallLate:
        method = self._timed_out.pop(event.request_id, None)
        if method is None or not event.ok:
            return event
        try:
            return CallLate(event.request_id, True, self._decode_result(method, event.result))
        except ApiError as exc:
            return CallLate(event.request_id, False, error=exc)

    def _remember(self, status: StationStatus) -> None:
        self._connected = {p.position for p in status.positions if p.dut_connected}

    # ---- sys ---------------------------------------------------------------------------------------------

    def hello(self, client: str = CLIENT, protocol: int = PROTOCOL) -> Call[Dict[str, Any]]:
        return self._call("hello", client, protocol)

    def status(self) -> Call[StationStatus]:
        call = self._call("status")
        call.then(self._remember)
        return call

    def subscribe(self, topics: List[str]) -> Call[None]:
        return self._call("subscribe", topics)   # asked for again after a reconnect

    def recover(self, position: int) -> Call[None]:
        return self._call("recover", position)

    # ---- dut ---------------------------------------------------------------------------------------------

    def connect_dut(self, position: int, config_type: str, config_file: str,
                    rpc: Optional[RpcAddress] = None) -> Call[ConnectResult]:
        return self._call("connect_dut", position, config_type, config_file, rpc)

    def reconnect_dut(self, position: int) -> Call[None]:
        return self._call("reconnect_dut", position)

    def disconnect_dut(self, position: int) -> Call[None]:
        return self._call("disconnect_dut", position)

    def probe(self, position: int, rpc: Optional[RpcAddress], timeout_s: float) -> Call[ProbeResult]:
        return self._call("probe", position, rpc, timeout_s)

    def load_phy(self, position: int, phy: PhySpec) -> Call[LoadPhyResult]:
        return self._call("load_phy", position, phy)

    def dut_info(self, position: int) -> Call[DutInfo]:
        return self._call("dut_info", position)

    def set_rpc_timeout(self, seconds: float) -> Call[None]:
        call = self._call("set_rpc_timeout", seconds)
        call.then(lambda _: setattr(self, "timeout_s", seconds))   # calls now default to the new timeout
        return call

    # ---- rf ----------------------------------------------------------------------------------------------

    def rf_paths(self) -> Call[List[str]]:
        return self._call("rf_paths")

    def rf_connect(self, position: int, path: str) -> Call[None]:
        return self._call("rf_connect", position, path)

    def rf_disconnect(self, position: int) -> Call[None]:
        return self._call("rf_disconnect", position)

    def prs_route(self, position: int, route: PrsRoute) -> Call[None]:
        return self._call("prs_route", position, route)

    def prs_signals(self, position: int) -> Call[PrsSignalCatalog]:
        return self._call("prs_signals", position)

    # ---- registers ---------------------------------------------------------------------------------------

    def register_tree(self, position: int) -> Call[List[PeripheralDef]]:
        return self._call("register_tree", position)

    def read_register(self, position: int, name: str) -> Call[int]:
        return self._call("read_register", position, name)

    def read_many(self, position: int, names: List[str],
                  include_read_sensitive: bool = False) -> Call[List[ReadManyItem]]:
        return self._call("read_many", position, names, include_read_sensitive)

    def write_register(self, position: int, name: str, value: int, confirm: bool = False,
                       verify: bool = True) -> Call[WriteResult]:
        return self._call("write_register", position, name, value, confirm, verify)

    def write_field(self, position: int, name: str, field: str, value: int,
                    confirm: bool = False, verify: bool = True) -> Call[WriteResult]:
        return self._call("write_field", position, name, field, value, confirm, verify)

    def watch(self, position: int, names: List[str], interval_s: float,
              include_read_sensitive: bool = False) -> Call[str]:
        return self._call("watch", position, names, interval_s, include_read_sensitive)

    def unwatch(self, sub_id: str) -> Call[None]:
        return self._call("unwatch", sub_id)

    # ---- activities ----------------------------------------------------------------------------------------

    def abort_activity(self, activity_id: str) -> Call[None]:
        return self._call("abort_activity", activity_id)

    def run_sequence(self, position: int, ops: List[Dict[str, Any]], stop_on_error: bool = True) -> Call[str]:
        return self._call("run_sequence", position, ops, stop_on_error)

    def list_tests(self) -> Call[List[StationTest]]:
        return self._call("list_tests")

    def run_tests(self, position: int, test_ids: List[str]) -> Call[str]:
        return self._call("run_tests", position, test_ids)

    # ---- instruments ---------------------------------------------------------------------------------------

    def list_instruments(self) -> Call[List[InstrumentFacts]]:
        return self._call("list_instruments")

    def connect_instrument(self, instrument_id: str, address: Optional[str] = None) -> Call[None]:
        return self._call("connect_instrument", instrument_id, address)

    def siggen_get(self, instrument_id: str) -> Call[SiggenConfig]:
        return self._call("siggen_get", instrument_id)

    def siggen_set(self, instrument_id: str, config: SiggenConfig) -> Call[None]:
        return self._call("siggen_set", instrument_id, config)

    def siggen_waveforms(self, instrument_id: str, reload: bool = False) -> Call[List[str]]:
        return self._call("siggen_waveforms", instrument_id, reload)

    def siggen_trigger(self, instrument_id: str, mode: str) -> Call[None]:
        return self._call("siggen_trigger", instrument_id, mode)

    def siggen_rf(self, instrument_id: str, on: bool) -> Call[None]:
        return self._call("siggen_rf", instrument_id, on)

    def chamber_read(self, instrument_id: str) -> Call[ChamberReading]:
        return self._call("chamber_read", instrument_id)

    def chamber_set_temp(self, instrument_id: str, celsius: float) -> Call[None]:
        return self._call("chamber_set_temp", instrument_id, celsius)

    def chamber_wait_stable(self, instrument_id: str, tolerance_c: float = 0.5, hold_s: float = 60,
                            timeout_s: float = 3600) -> Call[str]:
        return self._call("chamber_wait_stable", instrument_id, tolerance_c, hold_s, timeout_s)

    def eca_sources(self, instrument_id: str) -> Call[EcaSources]:
        return self._call("eca_sources", instrument_id)

    def eca_capture(self, instrument_id: str, spec: CaptureSpec) -> Call[str]:
        return self._call("eca_capture", instrument_id, spec)

    def eca_result(self, capture_id: str, offset: int = 0, count: int = 65536) -> Call[CapturePage]:
        return self._call("eca_result", capture_id, offset, count)

    # ---- memory and advanced -------------------------------------------------------------------------------

    def memory_read(self, position: int, address: int, size: int) -> Call[MemoryBlock]:
        return self._call("memory_read", position, address, size)

    def memory_write(self, position: int, address: int, value: int, size: int) -> Call[MemoryWriteRes]:
        return self._call("memory_write", position, address, value, size)

    def console_open(self, position: int) -> Call[str]:
        return self._call("console_open", position)

    def console_exec(self, session_id: str, code: str, mode: str = "auto") -> Call[ExecResult]:
        return self._call("console_exec", session_id, code, mode)

    def console_names(self, session_id: str) -> Call[List[NameInfo]]:
        return self._call("console_names", session_id)

    def console_close(self, session_id: str) -> Call[None]:
        return self._call("console_close", session_id)

    def custom_function(self, position: int, name: str, code: str,
                        session_id: Optional[str] = None) -> Call[ExecResult]:
        return self._call("custom_function", position, name, code, session_id)

    def dut_control_describe(self, position: int) -> Call[ApiTree]:
        return self._call("dut_control_describe", position)

    def dut_control_invoke(self, position: int, path: str, args: List[Any],
                           kwargs: Dict[str, Any]) -> Call[InvokeRes]:
        return self._call("dut_control_invoke", position, path, args, kwargs)
