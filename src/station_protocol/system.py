"""sys: handshake, status, event subscription and recovery; and the status.changed and call.late events."""

from __future__ import annotations

from typing import Any, List, Union

from typing_extensions import NotRequired, TypedDict

from station_protocol.common import POS, StationStatus
from station_protocol.errors import ApiError
from station_protocol.method import Event, Method, Param


class Hello(TypedDict):
    release_id: str
    protocol: int
    server_time: str          # ISO 8601 UTC


class CallLateData(TypedDict):
    request_id: Union[int, str]            # the JSON-RPC id of the call that timed out
    ok: bool
    result: NotRequired[Any]               # in the timed-out method's result shape
    error: NotRequired[ApiError]


METHODS = (
    Method("sys.hello", (Param("client", str), Param("protocol", int)), Hello),
    Method("sys.status", (), StationStatus),
    Method("sys.subscribe", (Param("topics", List[str]),), None),
    Method("sys.recover", (POS,), None),
)

STATUS_CHANGED = Event("status.changed", StationStatus, "status")
CALL_LATE = Event("call.late", CallLateData, None)
