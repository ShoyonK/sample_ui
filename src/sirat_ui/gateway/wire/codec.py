"""The app's models <-> JSON for the wire (station_protocol is the contract; this is the app's side of it).

decode(type, json) validates station data as one of the app's own types (models/ dataclasses, which stay free of
pydantic) with the protocol's strict rules (station_protocol.validate), and raises CodecError naming where the
JSON doesn't fit. A few app types travel in a different shape (WIRE_FORMS): those are validated as the
protocol's type and then converted.

encode() is the other direction: a dataclass is an object of its fields, a tuple or list an array, an enum its
value, a PHY carries its `kind` tag, and an ApiError is a JSON-RPC error object. to_wire() adds the shapes that
differ (the register tree).
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Any, Callable, Dict, List, Tuple

from station_protocol import dut as wire_dut
from station_protocol import registers as wire_registers
from station_protocol.jsonrpc import error_object
from station_protocol.validate import ValidationFailed, validate
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.wire.shapes import tree_from_wire, tree_to_wire
from sirat_ui.models.radio import WifiPhyConfig
from sirat_ui.models.registers import PeripheralDef
from sirat_ui.models.station import LpwPhy, PhySpec, WifiPhy

CodecError = ValidationFailed   # raised by decode; `path` says where

# Tagged unions: class -> the value of its "kind" key.
TAGS: Dict[type, str] = {LpwPhy: "lpw", WifiPhy: "wifi"}
TAG = "kind"


# ---- encode ---------------------------------------------------------------------------------------------------

def encode(value: Any) -> Any:
    """A model value as JSON."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value.value if isinstance(value, enum.Enum) else value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, ApiError):
        return error_object(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out = {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)}
        tag = TAGS.get(type(value))
        return {TAG: tag, **out} if tag else out
    if isinstance(value, dict):
        return {str(k.value if isinstance(k, enum.Enum) else k): encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [encode(v) for v in value]
    raise CodecError("", f"can't encode a {type(value).__name__}")


def to_wire(tp: Any, value: Any) -> Any:
    """A value of app type `tp` in its wire shape: the shape of its own (TO_WIRE), else encode()."""
    convert = TO_WIRE.get(tp)
    return convert(value) if convert is not None else encode(value)


# ---- decode ---------------------------------------------------------------------------------------------------

def _phy_from_wire(phy: Any) -> PhySpec:
    if phy[TAG] == "lpw":
        return LpwPhy(phy["name"])
    # the protocol's WifiPhyConfig, rebuilt as the app's (same fields)
    return WifiPhy(validate(WifiPhyConfig, encode(phy["config"])))


# App types whose wire form differs: (the protocol type to validate, the conversion to the app type).
WIRE_FORMS: Dict[Any, Tuple[Any, Callable[[Any], Any]]] = {
    PhySpec: (wire_dut.PhySpec, _phy_from_wire),
    List[PeripheralDef]: (wire_registers.RegisterTree, tree_from_wire),
}
TO_WIRE: Dict[Any, Callable[[Any], Any]] = {List[PeripheralDef]: tree_to_wire}


def decode(tp: Any, data: Any, path: str = "") -> Any:
    """`data` (parsed JSON) validated as app type `tp` and returned as the app's dataclasses. `path` prefixes the
    location in errors. Raises CodecError."""
    form = WIRE_FORMS.get(tp)
    if form is None:
        return validate(tp, data, path)
    return form[1](validate(form[0], data, path))
