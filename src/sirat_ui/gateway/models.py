"""Gateway result and event models (frontend side of the API contract)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from sirat_ui.core.registers import ChipInfo
from sirat_ui.core.wifi import WifiPhyConfig
from sirat_ui.core.requires import PositionFacts
from sirat_ui.gateway.errors import ApiError


@dataclass
class StationStatus:
    release_id: str
    positions: List[PositionFacts] = field(default_factory=list)
    claim: Optional[str] = None


@dataclass
class ConnectResult:
    chip: ChipInfo
    rpc_ok: bool = True


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
    written: int
    readback: int


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

@dataclass
class WatchValues:
    sub_id: str
    position: int
    ts: float
    values: Dict[str, int]


@dataclass
class ActivityProgress:
    activity_id: str
    position: int
    step: int
    total: int
    message: str


@dataclass
class ActivityFinished:
    activity_id: str
    position: int
    ok: bool
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[ApiError] = None


@dataclass
class LogLine:
    ts: float
    level: str
    source: str
    text: str


GatewayEvent = Union[StatusChanged, DutDisconnected, WatchValues, ActivityProgress, ActivityFinished, LogLine]
