"""automation: running a list of ops as one activity (automation.seq.run), and the ops themselves.

A client builds the ops from what the user saved: one op per step, tagged by `type`, each with an optional
`group` (what the op came from, echoed in activity.progress). The station validates the list against WireOp
before the run starts, so a malformed op fails the call with invalid_params instead of failing halfway through a
run. They stay plain JSON objects (TypedDicts).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import Field
from typing_extensions import Annotated, Literal, NotRequired, TypedDict

from station_protocol.common import ACTIVITY, POS
from station_protocol.method import Method, Param


class _Op(TypedDict):
    group: NotRequired[str]


class RegisterWriteOp(_Op):
    type: Literal["register_write"]
    register: str            # PERIPHERAL.REGISTER
    value: int


class FieldWriteOp(_Op):
    type: Literal["field_write"]
    register: str
    field: str
    value: int               # the field's value, not the register's


class RfSwitchOp(_Op):
    type: Literal["rf_switch"]
    path: str                # connected to the run's position


class LoadPhyOp(_Op):
    type: Literal["load_phy"]
    phy_name: str            # BLE_1M, IEEE802154_2p4G, ...
    method_name: NotRequired[str]


class WifiTxData(TypedDict):
    pkt_length: int
    num_pkts: int
    transmit_mode: str
    aggr_enable: bool


class WifiAdvancedData(TypedDict):
    ppdu_type: str
    gi_ltf: str
    dcm: bool
    bandwidth: str


class WifiConfigData(TypedDict):
    """A WiFi PHY config as a load_wifi_phy op carries it (dut.WifiPhyConfig's fields)."""
    mode: Literal["RX", "TX"]
    standard: str
    channel: int
    power_mode: str
    rate: str
    phy_name: str
    tx_params: NotRequired[Optional[WifiTxData]]
    advanced: NotRequired[Optional[WifiAdvancedData]]


class LoadWifiPhyOp(_Op):
    type: Literal["load_wifi_phy"]
    config: WifiConfigData


class SiggenConfigData(TypedDict):
    """A signal generator config as a signal_generator op carries it: frequency in Hz."""
    sg_type: str
    input_config_name: str
    frequency_hz: float
    power_dbm: float
    overrides: Dict[str, Any]


class SignalGeneratorOp(_Op):
    type: Literal["signal_generator"]
    instrument_id: str
    config: SiggenConfigData


class GfskPacketOp(_Op):
    type: Literal["gfsk_packet"]
    code: str                # generated Python run on the station


class CustomFunctionOp(_Op):
    type: Literal["custom_function"]
    function_name: str
    code: str                # copied in from the user's functions file


class DutControlMethodOp(_Op):
    type: Literal["dut_control_method"]
    method_path: str         # lpw.radio.SetChannel
    method_name: str
    params: Dict[str, Any]   # keyword arguments


class DutReconnectOp(_Op):
    type: Literal["dut_reconnect"]
    description: NotRequired[str]


class PrsRouteOp(_Op):
    type: Literal["prs_route"]
    signal: str
    pin: str
    channel: int


WireOp = Annotated[Union[RegisterWriteOp, FieldWriteOp, RfSwitchOp, LoadPhyOp, LoadWifiPhyOp, SignalGeneratorOp,
                         GfskPacketOp, CustomFunctionOp, DutControlMethodOp, DutReconnectOp, PrsRouteOp],
                   Field(discriminator="type")]
WireOps = Annotated[List[WireOp], Field(min_length=1)]

METHODS = (
    Method("automation.seq.run", (POS, Param("ops", WireOps), Param("stop_on_error", bool, True)), str, wrap=ACTIVITY,
           requires=("dut", "idle", "no_fault")),
)
