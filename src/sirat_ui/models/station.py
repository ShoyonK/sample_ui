"""Station API results and events (the frontend side of docs/API_DESIGN.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from sirat_ui.gateway.errors import ApiError
from sirat_ui.models.facts import InstrumentFacts, PositionFacts
from sirat_ui.models.radio import WifiPhyConfig
from sirat_ui.models.registers import ChipInfo


@dataclass
class StationStatus:
    release_id: str
    positions: List[PositionFacts] = field(default_factory=list)
    instruments: List[InstrumentFacts] = field(default_factory=list)
    claim: Optional[str] = None


@dataclass(frozen=True)
class RpcAddress:
    """Where a DUT's RPC server listens; None in calls means "the workspace config's address"."""
    host: str
    port: int


@dataclass
class ConnectResult:
    chip: ChipInfo
    rpc: Optional[RpcAddress] = None          # where the DUT was actually reached


@dataclass(frozen=True)
class ProbeResult:
    """dut.probe: can that address be reached? Never keeps or drops a connection."""
    ok: bool
    latency_ms: float = 0.0
    detail: str = ""


@dataclass
class DutInfo:
    """API doc dut.info: hw{}, rta{}, chip, revision. app{} holds firmware metadata when the DUT has it."""
    chip: str
    revision: str
    hw: Dict[str, Any] = field(default_factory=dict)
    rta: Dict[str, Any] = field(default_factory=dict)
    app: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WriteResult:
    """registers.write / write_field (API WriteRes). value_written is the whole register value written."""
    value_written: int
    value_readback: Optional[int]   # None when the register can't be read back (write-only)
    verified: bool = True           # False: the read-back differs. The write happened; the GUI warns (req 7)


@dataclass
class ReadManyItem:
    name: str
    value: Optional[int] = None
    error: Optional[ApiError] = None


# ---- events (pushed after sys.subscribe) ----

@dataclass
class StatusChanged:
    status: StationStatus


@dataclass
class DutDisconnected:
    position: int
    cause: str
    detected_by: str


# ---- PHY loading and PRS routing (req 23, req 24; docs/API_CHANGE_phy_and_prs.md) -------------------

@dataclass(frozen=True)
class LpwPhy:
    """A BLE or 802.15.4 PHY by name; the service calls reset_and_download_lpw_phy."""
    name: str


@dataclass(frozen=True)
class WifiPhy:
    """A WiFi PHY built from the WiFi PHY form; the service calls load_wifi_phy."""
    config: WifiPhyConfig


PhySpec = Union[LpwPhy, WifiPhy]


@dataclass(frozen=True)
class LoadPhyResult:
    name: str
    function: str = ""                                                     # what the service called
    overrides: Tuple[Tuple[str, str], ...] = ()                            # TestInputs overrides applied


@dataclass(frozen=True)
class PrsRoute:
    signal: str
    pin: str
    channel: int


@dataclass(frozen=True)
class PrsSignalCatalog:
    """The PRS signals the chip family's module defines (sorted), and where they came from."""
    family: str
    module: str
    signals: Tuple[str, ...]

# ---- instruments (req 25-30; docs/API_DESIGN.md "instruments") -------------------------------------------

@dataclass
class SiggenConfig:
    """What a signal generator is loaded with. The wire carries Hz; the GUI shows MHz."""
    sg_type: str = "PacketSrw"
    input_config_name: str = ""
    frequency_hz: float = 2440e6
    power_dbm: float = 0.0
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChamberReading:
    actual_c: float
    target_c: float
    stable: bool


@dataclass(frozen=True)
class EcaSources:
    channels: Tuple[str, ...]
    triggers: Tuple[str, ...]          # trigger sources; "immediate" is always allowed too


EDGES = ("rising", "falling", "either")


@dataclass(frozen=True)
class CaptureSpec:
    channels: Tuple[str, ...]
    trigger: str                       # a trigger source, or "immediate"
    edge: str = "rising"
    sample_rate_hz: float = 1e6
    duration_s: float = 0.01
    pretrigger_pct: int = 10


@dataclass(frozen=True)
class CaptureMeta:
    spec: CaptureSpec
    started_at: float
    sample_count: int
    chip: str = ""
    pos: int = 0


@dataclass(frozen=True)
class CapturePage:
    """One page of a capture: channel -> base64 little-endian int16 samples for [offset, offset+count)."""
    meta: CaptureMeta
    offset: int
    count: int
    channels: Dict[str, str]
    more: bool


# ---- memory and advanced (req 15, 19, 20, 22; docs/API_DESIGN.md "memory", "advanced") ------------------------

@dataclass(frozen=True)
class MemoryBlock:
    """memory.read: `address` is the aligned start actually read; data is base64."""
    address: int
    data: str


@dataclass(frozen=True)
class MemoryWriteRes:
    address: int
    value_written: int
    value_readback: int


@dataclass(frozen=True)
class Traceback:
    type: str
    message: str
    text: str


@dataclass(frozen=True)
class ExecResult:
    """Console and custom functions. result_text is None when the code had no value."""
    stdout: str = ""
    stderr: str = ""
    result_text: Optional[str] = None
    error: Optional[Traceback] = None


@dataclass(frozen=True)
class NameInfo:
    name: str
    type: str
    doc: str = ""


@dataclass(frozen=True)
class ApiParam:
    name: str
    annotation: str
    default_repr: Optional[str]
    required: bool


@dataclass(frozen=True)
class ApiMethod:
    name: str
    path: str
    signature: str
    doc: str
    params: Tuple[ApiParam, ...] = ()


@dataclass(frozen=True)
class ApiModule:
    name: str
    path: str
    methods: Tuple[ApiMethod, ...] = ()


@dataclass(frozen=True)
class ApiPackage:
    name: str
    modules: Tuple[ApiModule, ...] = ()


@dataclass(frozen=True)
class ApiTree:
    packages: Tuple[ApiPackage, ...] = ()


@dataclass(frozen=True)
class InvokeRes:
    result_text: str
    result_json: Any
    result_type: str


@dataclass
class WatchValues:
    sub_id: str
    position: int
    ts: float
    values: Dict[str, int]


@dataclass
class ActivityProgress:
    activity_id: str
    position: int            # 0 for an instrument's activity
    step: int
    total: int
    message: str
    group: str = ""          # the action the current op came from (automation.seq.run)
    instrument_id: str = ""


@dataclass
class ActivityFinished:
    activity_id: str
    position: int
    ok: bool
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[ApiError] = None
    instrument_id: str = ""
    result: Any = None       # e.g. {capture_id} for instruments.eca.capture


@dataclass
class LogLine:
    ts: float
    level: str
    source: str
    text: str
    position: Optional[int] = None


@dataclass
class CallLate:
    """A call that timed out finished after all: did it work? (data.still_running was true on the timeout)."""
    request_id: int
    ok: bool
    result: Any = None
    error: Optional[ApiError] = None


GatewayEvent = Union[StatusChanged, DutDisconnected, WatchValues, ActivityProgress, ActivityFinished, LogLine,
                     CallLate]
