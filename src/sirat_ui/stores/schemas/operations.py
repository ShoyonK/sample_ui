"""Actions file (~/.sirat_actions.json, req 13): every operation type in req 13 "Action Types Supported".

An action with any invalid operation is skipped as a whole: running half an action could leave the DUT in a
state nobody intended. Unknown keys inside an operation are kept, so files from newer or older GUIs round-trip.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, field_validator, model_validator
from typing_extensions import Annotated

from sirat_ui.core import wifi
from sirat_ui.core.ops import op_kind
from sirat_ui.core.prs import channel_problem
from sirat_ui.stores.schemas.common import NonEmpty, RegisterName, RegisterValue
from sirat_ui.stores.schemas.report import Report, expect_dict, validate_entry


class _Op(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# `register` would shadow BaseModel.register (an ABC classmethod), so the field is register_ and the JSON key
# stays "register" through the alias; dumps use by_alias=True.
RegisterField = Annotated[RegisterName, Field(alias="register")]


class RegisterWriteOp(_Op):
    register_: RegisterField
    value: RegisterValue


class FieldWriteOp(_Op):
    register_: RegisterField
    field: NonEmpty
    value: RegisterValue


class CustomFunctionOp(_Op):
    type: Literal["custom_function"]
    function_name: NonEmpty


class RfSwitchOp(_Op):
    type: Literal["rf_switch"]
    path: NonEmpty
    dut_position: int = Field(1, ge=1, le=4)


class SignalGeneratorOp(_Op):
    type: Literal["signal_generator"]
    sg_type: NonEmpty
    input_config_name: str = ""
    frequency_mhz: float = Field(gt=0)
    power_dbm: float = Field(ge=-150, le=30)
    overrides: Dict[str, Any] = {}
    code: str = ""


class LoadPhyOp(_Op):
    type: Literal["load_phy"]
    phy_name: NonEmpty
    method_name: str = ""


class WifiTxModel(BaseModel):
    pkt_length: int = Field(ge=1, le=wifi.MAX_PKT_LENGTH)
    num_pkts: int = Field(ge=0, le=wifi.MAX_NUM_PKTS)
    transmit_mode: Literal["BURST", "CONTINUES", "STREAM"]
    aggr_enable: bool


class WifiAdvancedModel(BaseModel):
    ppdu_type: NonEmpty
    gi_ltf: NonEmpty
    dcm: int = Field(ge=0, le=1)
    bandwidth: Literal["BW_20MHz", "BW_40MHz", "BW_80MHz", "BW_160MHz"]


class WifiConfigModel(BaseModel):
    """Req 23 "WiFi Config Structure"; the channel must belong to the standard's band."""
    model_config = ConfigDict(extra="allow")
    mode: Literal["RX", "TX"]
    standard: str
    channel: int
    power_mode: Literal["HP", "LP", "MP"]
    rate: NonEmpty
    phy_name: NonEmpty
    tx_params: Optional[WifiTxModel] = None
    advanced: Optional[WifiAdvancedModel] = None

    @field_validator("standard")
    @classmethod
    def _known_standard(cls, value: str) -> str:
        if value not in wifi.STANDARDS:
            raise ValueError(f"unknown standard '{value}' (use one of {', '.join(wifi.STANDARDS)})")
        return value

    @model_validator(mode="after")
    def _channel_in_band(self) -> "WifiConfigModel":
        if self.channel not in wifi.channels(self.standard):
            raise ValueError(f"channel {self.channel} isn't available for {self.standard}")
        return self


class LoadWifiPhyOp(_Op):
    type: Literal["load_wifi_phy"]
    config: WifiConfigModel


class DutControlMethodOp(_Op):
    type: Literal["dut_control_method"]
    method_path: NonEmpty
    method_name: str = ""
    params: Dict[str, Any] = {}


class DutReconnectOp(_Op):
    type: Literal["dut_reconnect"]
    description: str = ""


class SequenceOp(_Op):
    type: Literal["sequence"]
    sequence_name: NonEmpty
    action_names: List[NonEmpty] = []


class PrsRouteOp(_Op):
    type: Literal["prs_route"]
    signal: NonEmpty
    pin: Annotated[str, Field(pattern=r"^P[A-D][0-7]$")]
    channel: int = Field(ge=0, le=11)

    @model_validator(mode="after")
    def _port_allows_channel(self) -> "PrsRouteOp":
        problem = channel_problem(self.pin, self.channel)
        if problem:
            raise ValueError(problem)
        return self


class GfskPacketOp(_Op):
    type: Literal["gfsk_packet"]
    code: str


OPERATION_MODELS: Dict[str, Type[_Op]] = {
    "register_write": RegisterWriteOp, "field_write": FieldWriteOp, "custom_function": CustomFunctionOp,
    "rf_switch": RfSwitchOp, "signal_generator": SignalGeneratorOp, "load_phy": LoadPhyOp,
    "load_wifi_phy": LoadWifiPhyOp, "dut_control_method": DutControlMethodOp, "dut_reconnect": DutReconnectOp,
    "sequence": SequenceOp, "prs_route": PrsRouteOp, "gfsk_packet": GfskPacketOp,
}


def validate_operation(op: Any) -> Dict[str, Any]:
    """One operation, checked against its type's model. Returns it normalized (e.g. "0x1F" -> 31)."""
    if not isinstance(op, dict):
        raise ValueError(f"an operation must be an object, not {type(op).__name__}")
    kind = op_kind(op)
    model = OPERATION_MODELS.get(kind)
    if model is None:
        raise ValueError(f"unknown operation type '{kind}'")
    try:
        return model.model_validate(op).model_dump(mode="json", exclude_unset=True, by_alias=True)
    except ValidationError as error:
        details = "; ".join(f"{'.'.join(str(p) for p in e['loc']) or kind}: {e['msg'].removeprefix('Value error, ')}"
                            for e in error.errors())
        raise ValueError(f"{kind}: {details}") from None


Operation = Annotated[Dict[str, Any], BeforeValidator(validate_operation)]


class ActionModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    operations: List[Operation]
    enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def _legacy_formats(cls, value: Any) -> Any:
        """Req 13 legacy formats: [operations] and {register: value}."""
        if isinstance(value, list):
            return {"operations": value}
        if isinstance(value, dict) and "operations" not in value:
            return {"operations": [{"register": reg, "value": val} for reg, val in value.items()]}
        return value


def clean_actions(raw: Any, report: Report) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, value in expect_dict(raw, report).items():
        action = validate_entry(ActionModel, value, report, name)
        if action is not None:
            out[name] = action.model_dump(mode="json")
    return out
