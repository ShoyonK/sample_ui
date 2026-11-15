"""The JSON-RPC 2.0 envelope (docs/STATION_API.md "Protocol").

Builds and reads the four messages: request, reply, error reply and notification (events). Errors carry an
integer `code` and the Station API's string code as `data.reason`; ApiError is converted both ways here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from station_protocol.errors import ApiError, ErrorCode

VERSION = "2.0"
META = "_meta"   # reserved key in params for call options (timeout_ms)

PARSE_ERROR = -32700
INVALID_REQUEST = -32600

# Station API code -> JSON-RPC code. -32601..-32603 are JSON-RPC's own; -32001.. are server-defined.
CODES: Dict[ErrorCode, int] = {
    ErrorCode.UNKNOWN_METHOD: -32601,
    ErrorCode.INVALID_PARAMS: -32602,
    ErrorCode.INTERNAL: -32603,
    ErrorCode.WRONG_STATE: -32001,
    ErrorCode.TIMEOUT: -32002,
    ErrorCode.BUSY: -32003,
    ErrorCode.CLAIMED: -32004,
    ErrorCode.CONFIRMATION_REQUIRED: -32005,
    ErrorCode.READ_SENSITIVE: -32006,
    ErrorCode.ACCESS_DENIED: -32007,
    ErrorCode.OUT_OF_RANGE: -32008,
    ErrorCode.NOT_FOUND: -32009,
    ErrorCode.DUT_DISCONNECTED: -32010,
    ErrorCode.INSTRUMENT_ERROR: -32011,
    ErrorCode.HARDWARE_ERROR: -32012,
    ErrorCode.ABORTED: -32013,
}
_BY_NUMBER = {number: code for code, number in CODES.items()}
_BY_NUMBER.update({PARSE_ERROR: ErrorCode.INVALID_PARAMS, INVALID_REQUEST: ErrorCode.INVALID_PARAMS})
_BY_NAME = {code.value: code for code in ErrorCode}

RequestId = Union[int, str]


class ProtocolError(Exception):
    """A message that isn't valid JSON-RPC 2.0. `code` is the JSON-RPC code to answer with."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---- errors ------------------------------------------------------------------------------------------------

def error_object(error: ApiError, number: Optional[int] = None) -> Dict[str, Any]:
    """An ApiError as a JSON-RPC error object: {code, message, data: {reason, ...}}."""
    return {"code": number if number is not None else CODES[error.code], "message": error.message,
            "data": {"reason": error.code.value, **error.data}}


def api_error(obj: Any) -> ApiError:
    """A JSON-RPC error object as an ApiError: by data.reason, else by the integer code, else internal."""
    if not isinstance(obj, dict):
        return ApiError(ErrorCode.INTERNAL, f"Malformed error: {obj!r}")
    data = dict(obj.get("data") or {}) if isinstance(obj.get("data"), dict) else {}
    reason = data.pop("reason", None)
    code = _BY_NAME.get(reason) if isinstance(reason, str) else None
    if code is None:
        number = obj.get("code")
        code = _BY_NUMBER.get(number, ErrorCode.INTERNAL) if isinstance(number, int) else ErrorCode.INTERNAL
    return ApiError(code, str(obj.get("message") or ""), data)


# ---- building -------------------------------------------------------------------------------------------------

def request(request_id: RequestId, method: str, params: Dict[str, Any],
            timeout_ms: Optional[int] = None) -> Dict[str, Any]:
    if timeout_ms is not None:
        params = {**params, META: {"timeout_ms": timeout_ms}}
    return {"jsonrpc": VERSION, "id": request_id, "method": method, "params": params}


def reply(request_id: Optional[RequestId], result: Any) -> Dict[str, Any]:
    return {"jsonrpc": VERSION, "id": request_id, "result": result}


def error_reply(request_id: Optional[RequestId], error: Dict[str, Any]) -> Dict[str, Any]:
    """`request_id` is None when the request's id couldn't be read (parse error, invalid request)."""
    return {"jsonrpc": VERSION, "id": request_id, "error": error}


def protocol_error_reply(request_id: Optional[RequestId], error: ProtocolError) -> Dict[str, Any]:
    reason = ErrorCode.UNKNOWN_METHOD if error.code == CODES[ErrorCode.UNKNOWN_METHOD] else ErrorCode.INVALID_PARAMS
    return error_reply(request_id, error_object(ApiError(reason, error.message), error.code))


def notification(method: str, seq: int, data: Any) -> Dict[str, Any]:
    """An event: no id; params hold the connection's event `seq` and the event's data."""
    return {"jsonrpc": VERSION, "method": method, "params": {"seq": seq, "data": data}}


# ---- reading ---------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Request:
    """A request (or, with no id, a client notification). `params` has `_meta` removed."""
    id: Optional[RequestId]
    method: str
    params: Dict[str, Any]
    timeout_ms: Optional[int] = None

    @property
    def is_notification(self) -> bool:
        return self.id is None


@dataclass(frozen=True)
class Reply:
    """A reply: `error` is None on success."""
    id: RequestId
    result: Any = None
    error: Optional[ApiError] = None


@dataclass(frozen=True)
class Notification:
    """An event from the server."""
    method: str
    seq: int
    data: Any


def _check_version(message: Any) -> Dict[str, Any]:
    if isinstance(message, list):
        raise ProtocolError(INVALID_REQUEST, "Batches aren't supported")
    if not isinstance(message, dict) or message.get("jsonrpc") != VERSION:
        raise ProtocolError(INVALID_REQUEST, 'Not a JSON-RPC 2.0 message (needs "jsonrpc": "2.0")')
    return message


def read_request(message: Any) -> Request:
    """What the server receives. Raises ProtocolError for anything that isn't a valid request."""
    message = _check_version(message)
    method = message.get("method")
    if not isinstance(method, str) or not method:
        raise ProtocolError(INVALID_REQUEST, "A request needs a method name")
    request_id = message.get("id")
    if request_id is not None and (isinstance(request_id, bool) or not isinstance(request_id, (int, str))):
        raise ProtocolError(INVALID_REQUEST, "id must be a number or a string")
    params = message.get("params", {})
    if not isinstance(params, dict):
        raise ProtocolError(-32602, "params must be an object of named parameters")
    params = dict(params)
    meta = params.pop(META, None) or {}
    timeout = meta.get("timeout_ms") if isinstance(meta, dict) else None
    return Request(request_id, method, params, timeout if isinstance(timeout, int) else None)


def read_incoming(message: Any) -> Union[Reply, Notification]:
    """What the client receives: a reply to one of its requests, or an event. Raises ProtocolError otherwise."""
    message = _check_version(message)
    if "id" not in message:
        params = message.get("params")
        if not isinstance(message.get("method"), str) or not isinstance(params, dict):
            raise ProtocolError(INVALID_REQUEST, "A notification needs a method and params")
        seq = params.get("seq")
        return Notification(message["method"], seq if isinstance(seq, int) else -1, params.get("data"))
    if "error" in message:
        return Reply(message["id"], error=api_error(message["error"]))
    if "result" not in message:
        raise ProtocolError(INVALID_REQUEST, "A reply needs a result or an error")
    return Reply(message["id"], result=message["result"])
