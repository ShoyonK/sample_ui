"""The station's interfaces, one per area of docs/API_DESIGN.md (revision 2).

Each service depends on the area it uses (RegistersPort, InstrumentsPort...), not on the whole station, so a
change in one area touches only its users. StationGateway combines them all: FakeStationGateway implements
it today, and ApiStationGateway (client SDK adapter) will later.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from station_protocol import PROTOCOL_VERSION
from sibench_ui.core.observable import Event
from sibench_ui.gateway.call import Call
from sibench_ui.models.facts import InstrumentFacts
from sibench_ui.models.registers import PeripheralDef
from sibench_ui.models.station import (ApiTree, CapturePage, CaptureSpec, ChamberReading, ConnectResult, DutInfo,
                                     EcaSources, ExecResult, InvokeRes, LoadPhyResult, MemoryBlock, MemoryWriteRes,
                                     NameInfo, PhySpec, ProbeResult, PrsRoute, PrsSignalCatalog, ReadManyItem,
                                     RpcAddress, SiggenConfig, StationStatus, StationTest, WriteResult)


PROTOCOL = PROTOCOL_VERSION   # the Station API protocol this client speaks (station_protocol)
CLIENT = "sibench-gui"  # what the GUI calls itself in sys.hello


class EventSource(Protocol):
    """Something that pushes GatewayEvents through `events`."""
    events: Event  # emits GatewayEvent instances (models/station.py)


class SystemPort(EventSource, Protocol):
    """sys.*: handshake, status, event subscription and recovery."""
    def hello(self, client: str = CLIENT, protocol: int = PROTOCOL) -> Call[Dict[str, Any]]: ...
    # -> {release_id, protocol, server_time}
    def status(self) -> Call[StationStatus]: ...
    def subscribe(self, topics: List[str]) -> Call[None]: ...
    def recover(self, position: int) -> Call[None]: ...


class DutPort(Protocol):
    """dut.*: connecting the DUT, PHYs, info and the RPC timeout."""
    def connect_dut(self, position: int, config_type: str, config_file: str,
                    rpc: Optional[RpcAddress] = None) -> Call[ConnectResult]: ...   # rpc None: workspace config
    def reconnect_dut(self, position: int) -> Call[None]: ...        # RPC only (rpc_io.Connect), keeps the bench setup
    def disconnect_dut(self, position: int) -> Call[None]: ...
    def probe(self, position: int, rpc: Optional[RpcAddress], timeout_s: float) -> Call[ProbeResult]: ...
    def load_phy(self, position: int, phy: PhySpec) -> Call[LoadPhyResult]: ...
    def dut_info(self, position: int) -> Call[DutInfo]: ...
    def set_rpc_timeout(self, seconds: float) -> Call[None]: ...


class RfPort(Protocol):
    """Req 24 PRS routing and req 28 RF switch."""
    def rf_paths(self) -> Call[List[str]]: ...
    def rf_connect(self, position: int, path: str) -> Call[None]: ...   # sets the position's rf_path fact
    def rf_disconnect(self, position: int) -> Call[None]: ...
    def prs_route(self, position: int, route: PrsRoute) -> Call[None]: ...
    def prs_signals(self, position: int) -> Call[PrsSignalCatalog]: ...  # docs/API_DESIGN.md "rf"


class RegistersPort(EventSource, Protocol):
    """registers.*: the tree, reads, checked writes and watch subscriptions."""
    def register_tree(self, position: int) -> Call[List[PeripheralDef]]: ...
    def read_register(self, position: int, name: str) -> Call[int]: ...
    def read_many(self, position: int, names: List[str],
                  include_read_sensitive: bool = False) -> Call[List[ReadManyItem]]: ...
    def write_register(self, position: int, name: str, value: int, confirm: bool = False,
                       verify: bool = True) -> Call[WriteResult]: ...
    def write_field(self, position: int, name: str, field: str, value: int,
                    confirm: bool = False, verify: bool = True) -> Call[WriteResult]: ...
    def watch(self, position: int, names: List[str], interval_s: float,
              include_read_sensitive: bool = False) -> Call[str]: ...                 # -> subscription id
    def unwatch(self, sub_id: str) -> Call[None]: ...


class ActivityPort(EventSource, Protocol):
    """Long-running work reports through activity.progress / activity.finished events."""
    def abort_activity(self, activity_id: str) -> Call[None]: ...


class AutomationPort(ActivityPort, Protocol):
    """automation.seq.run: run a batch of ops as one activity."""
    def run_sequence(self, position: int, ops: List[Dict[str, Any]],
                     stop_on_error: bool = True) -> Call[str]: ...                         # -> activity id


class TestsPort(ActivityPort, Protocol):
    """Req 33. A run is an activity: one progress event as each test starts and one with its result as it ends."""
    def list_tests(self) -> Call[List[StationTest]]: ...
    def run_tests(self, position: int, test_ids: List[str]) -> Call[str]: ...   # -> activity id


class InstrumentsPort(ActivityPort, Protocol):
    """Req 25-30. Chamber waits and ECA captures are activities."""
    def list_instruments(self) -> Call[List[InstrumentFacts]]: ...
    def connect_instrument(self, instrument_id: str, address: Optional[str] = None) -> Call[None]: ...
    # address None: the station's configured address
    def siggen_get(self, instrument_id: str) -> Call[SiggenConfig]: ...
    def siggen_set(self, instrument_id: str, config: SiggenConfig) -> Call[None]: ...
    def siggen_waveforms(self, instrument_id: str, reload: bool = False) -> Call[List[str]]: ...
    def siggen_trigger(self, instrument_id: str, mode: str) -> Call[None]: ...      # infinite | single
    def siggen_rf(self, instrument_id: str, on: bool) -> Call[None]: ...
    def chamber_read(self, instrument_id: str) -> Call[ChamberReading]: ...
    def chamber_set_temp(self, instrument_id: str, celsius: float) -> Call[None]: ...
    def chamber_wait_stable(self, instrument_id: str, tolerance_c: float = 0.5, hold_s: float = 60,
                            timeout_s: float = 3600) -> Call[str]: ...           # -> activity id
    def eca_sources(self, instrument_id: str) -> Call[EcaSources]: ...
    def eca_capture(self, instrument_id: str, spec: CaptureSpec) -> Call[str]: ...  # -> activity id
    def eca_result(self, capture_id: str, offset: int = 0, count: int = 65536) -> Call[CapturePage]: ...


class MemoryPort(Protocol):
    """Req 19."""
    def memory_read(self, position: int, address: int, size: int) -> Call[MemoryBlock]: ...   # size 1..4096
    def memory_write(self, position: int, address: int, value: int, size: int) -> Call[MemoryWriteRes]: ...  # 1|2|4


class AdvancedPort(Protocol):
    """Req 15 custom functions, 20 console, 22 DUT control."""
    def console_open(self, position: int) -> Call[str]: ...                          # -> session id
    def console_exec(self, session_id: str, code: str, mode: str = "auto") -> Call[ExecResult]: ...
    def console_names(self, session_id: str) -> Call[List[NameInfo]]: ...
    def console_close(self, session_id: str) -> Call[None]: ...
    def custom_function(self, position: int, name: str, code: str,
                        session_id: Optional[str] = None) -> Call[ExecResult]: ...
    def dut_control_describe(self, position: int) -> Call[ApiTree]: ...
    def dut_control_invoke(self, position: int, path: str, args: List[Any],
                           kwargs: Dict[str, Any]) -> Call[InvokeRes]: ...


class StationGateway(SystemPort, DutPort, RfPort, RegistersPort, AutomationPort, TestsPort, InstrumentsPort,
                     MemoryPort, AdvancedPort, Protocol):
    """Everything. Only the composition root and the backends need the whole station."""
