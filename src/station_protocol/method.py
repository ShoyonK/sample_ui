"""How a method is described: its wire name, parameters, result, and the state it requires.

Each group module (system.py, dut.py, registers.py...) declares its methods with these; methods.py collects
them. A server uses `check_params` to turn a request's params into validated values; a client uses
`read_result` to check a reply. Both follow docs/STATION_API.md: results are objects, a method with `wrap` sends
its single value as {wrap: value}, and a method with no result (`result` None) answers {}.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from station_protocol.errors import ApiError, ErrorCode
from station_protocol.validate import ValidationFailed, validate


class _Required:
    def __repr__(self) -> str:
        return "REQUIRED"


REQUIRED: Any = _Required()


@dataclass(frozen=True)
class Param:
    """One parameter: its wire name, type, and default (REQUIRED when it has none)."""
    wire: str
    type: Any
    default: Any = REQUIRED

    @property
    def required(self) -> bool:
        return self.default is REQUIRED


@dataclass(frozen=True)
class Method:
    wire: str                              # "registers.read"
    params: Tuple[Param, ...]              # in the order a client library's function takes them
    result: Any                            # the result's type (the wrapped value's type when `wrap` is set)
    wrap: str = ""                         # the result travels as {wrap: value}
    requires: Tuple[str, ...] = ()         # state the call needs (STATION_API.md "Requires"): dut, idle...

    @property
    def group(self) -> str:
        return self.wire.split(".")[0]


def check_params(method: Method, params: Dict[str, Any]) -> Dict[str, Any]:
    """A request's params validated, with defaults filled in: {wire name: value}. Raises ApiError(INVALID_PARAMS)
    with data.param for an unknown, missing or badly typed parameter."""
    unknown = sorted(set(params) - {p.wire for p in method.params})
    if unknown:
        raise ApiError(ErrorCode.INVALID_PARAMS, f"Unknown parameter {unknown[0]} for {method.wire}",
                       {"param": unknown[0]})
    out: Dict[str, Any] = {}
    for param in method.params:
        if param.wire in params:
            try:
                out[param.wire] = validate(param.type, params[param.wire], param.wire)
            except ValidationFailed as exc:
                raise ApiError(ErrorCode.INVALID_PARAMS, str(exc), {"param": exc.path or param.wire}) from None
        elif param.required:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"{param.wire} is required for {method.wire}",
                           {"param": param.wire})
        else:
            out[param.wire] = param.default
    return out


def unwrap(method: Method, raw: Any) -> Any:
    """The result value inside a reply: raw[wrap] for a wrapped result, None for Empty, else raw itself. Raises
    ValidationFailed when a wrapped result isn't an object holding its key."""
    if method.result is None:
        return None
    if method.wrap:
        if not isinstance(raw, dict) or method.wrap not in raw:
            raise ValidationFailed("", f"must be an object with {method.wrap}")
        return raw[method.wrap]
    return raw


def read_result(method: Method, raw: Any) -> Any:
    """A reply's result validated as the method's result type (see unwrap). Raises ValidationFailed."""
    value = unwrap(method, raw)
    return None if method.result is None else validate(method.result, value, method.wrap)


def wrap_result(method: Method, value: Any) -> Any:
    """What a server sends for a result value that is already JSON: {} for Empty, {wrap: value}, or the value."""
    if method.result is None:
        return {}
    return {method.wrap: value} if method.wrap else value


@dataclass(frozen=True)
class Event:
    """A notification the server sends: its name, its data's type, and the sys.subscribe topic that brings it
    (None: it goes only to the connection whose call it is about, like call.late)."""
    name: str
    data: Any
    topic: Optional[str]
