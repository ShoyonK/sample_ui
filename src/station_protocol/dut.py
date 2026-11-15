"""dut: connecting a DUT at a position, its info, PHYs and the RPC timeout; and the dut.disconnected event."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import Field
from typing_extensions import Annotated, Literal, TypedDict

from station_protocol.common import POS, ChipInfo, RpcAddress
from station_protocol.method import Event, Method, Param

RpcTimeout = Annotated[float, Field(ge=1, le=300)]
ConfigType = Literal["EFX", "EFR32"]
Mode = Literal["RX", "TX"]


@dataclass
class ConnectResult:
    """dut.connect: the chip, and where the DUT was reached."""
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


@dataclass(frozen=True)
class WifiTxParams:
    """WiFi TX settings (only sent for TX)."""
    pkt_length: int
    num_pkts: int
    transmit_mode: str
    aggr_enable: bool


@dataclass(frozen=True)
class WifiAdvanced:
    """802.11ax/be settings (only sent when enabled)."""
    ppdu_type: str
    gi_ltf: str
    dcm: bool
    bandwidth: str


@dataclass(frozen=True)
class WifiPhyConfig:
    """What load_wifi_phy gets (req 23 "WiFi Config Structure")."""
    mode: Mode
    standard: str
    channel: int
    power_mode: str
    rate: str  # Mb/s for b/g/a, MCS index for n/ac/ax/be
    phy_name: str
    tx_params: Optional[WifiTxParams] = None
    advanced: Optional[WifiAdvanced] = None


class LpwPhyWire(TypedDict):
    kind: Literal["lpw"]
    name: str


class WifiPhyWire(TypedDict):
    kind: Literal["wifi"]
    config: WifiPhyConfig


# dut.load_phy's phy: a BLE / 802.15.4 PHY by name, or a WiFi PHY config, tagged by `kind`
PhySpec = Annotated[Union[LpwPhyWire, WifiPhyWire], Field(discriminator="kind")]


@dataclass(frozen=True)
class LoadPhyResult:
    """dut.load_phy: the PHY, the function the service called, the overrides."""
    name: str
    function: str = ""                                                     # what the service called
    overrides: Tuple[Tuple[str, str], ...] = ()                            # TestInputs overrides applied


class DutDisconnectedData(TypedDict):
    pos: int
    cause: str
    detected_by: str           # heartbeat, registers.read, station connection...


METHODS = (
    Method("dut.connect", (POS, Param("config_type", ConfigType), Param("config_file", str),
                           Param("rpc", Optional[RpcAddress], None)), ConnectResult, requires=("no_fault",)),
    Method("dut.reconnect", (POS,), None, requires=("no_fault",)),
    Method("dut.disconnect", (POS,), None),
    Method("dut.probe", (POS, Param("rpc", Optional[RpcAddress]), Param("timeout_s", float)), ProbeResult),
    Method("dut.load_phy", (POS, Param("phy", PhySpec)), LoadPhyResult, requires=("dut", "idle")),
    Method("dut.info", (POS,), DutInfo, requires=("dut",)),
    Method("dut.set_rpc_timeout", (Param("seconds", RpcTimeout),), None),
)

DUT_DISCONNECTED = Event("dut.disconnected", DutDisconnectedData, "status")
