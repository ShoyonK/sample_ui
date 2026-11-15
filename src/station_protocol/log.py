"""log: the station's log lines, as the log.line event (no methods)."""

from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from station_protocol.method import Event


class LogLineData(TypedDict):
    ts: float
    level: str                 # debug, info, success, warning, error
    source: str
    text: str
    pos: NotRequired[int]


LOG_LINE = Event("log.line", LogLineData, "log")
