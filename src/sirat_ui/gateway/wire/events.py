"""The app's GatewayEvents <-> the protocol's notifications (station_protocol.catalog.EVENTS).

Each event's wire data is declared in the protocol (DutDisconnectedData, WatchData...): a DUT position is `pos`;
an activity belongs to a position or an instrument, so activity.* carries `pos` or `instrument_id`, not both;
optional keys are left out when they have no value. status.changed's data is the StationStatus itself, decoded
straight into the app's model. Decoding validates the data, then builds the app's event.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, NamedTuple, Tuple

from station_protocol.catalog import BY_EVENT
from sirat_ui.gateway.wire.codec import decode, encode
from sirat_ui.models.station import (ActivityFinished, ActivityProgress, CallLate, DutDisconnected, GatewayEvent,
                                     LogLine, StationStatus, StatusChanged, WatchValues)


def _drop_empty(data: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        if data.get(key) in (None, ""):
            data.pop(key, None)
    return data


def _owner(position: int, instrument_id: str) -> Dict[str, Any]:
    return {"pos": position} if position else {"instrument_id": instrument_id}


def _progress_to_wire(e: ActivityProgress) -> Dict[str, Any]:
    return _drop_empty({"activity_id": e.activity_id, **_owner(e.position, e.instrument_id), "step": e.step,
                        "total": e.total, "message": e.message, "group": e.group, "result": e.result},
                       "group", "result")


def _progress_from_wire(d: Any) -> ActivityProgress:
    return ActivityProgress(d["activity_id"], d.get("pos", 0), d["step"], d["total"], d["message"],
                            d.get("group", ""), d.get("instrument_id", ""), d.get("result"))


def _finished_to_wire(e: ActivityFinished) -> Dict[str, Any]:
    return _drop_empty({"activity_id": e.activity_id, **_owner(e.position, e.instrument_id), "ok": e.ok,
                        "results": encode(e.results), "error": encode(e.error), "result": encode(e.result)},
                       "error", "result")


def _finished_from_wire(d: Any) -> ActivityFinished:
    return ActivityFinished(d["activity_id"], d.get("pos", 0), d["ok"], list(d["results"]), d.get("error"),
                            d.get("instrument_id", ""), d.get("result"))


def _late_to_wire(e: CallLate) -> Dict[str, Any]:
    out: Dict[str, Any] = {"request_id": e.request_id, "ok": e.ok}
    out.update({"result": encode(e.result)} if e.ok else {"error": encode(e.error)})
    return out


class EventMap(NamedTuple):
    name: str                          # the notification's method
    data: Any                          # the type its data is validated as
    to_wire: Callable[[Any], Any]
    from_wire: Callable[[Any], Any]


def _map(name: str, to_wire: Callable[[Any], Any], from_wire: Callable[[Any], Any], data: Any = None) -> EventMap:
    return EventMap(name, data if data is not None else BY_EVENT[name].data, to_wire, from_wire)


EVENTS: Dict[type, EventMap] = {
    StatusChanged: _map("status.changed", lambda e: encode(e.status), StatusChanged, data=StationStatus),
    DutDisconnected: _map("dut.disconnected",
                          lambda e: {"pos": e.position, "cause": e.cause, "detected_by": e.detected_by},
                          lambda d: DutDisconnected(d["pos"], d["cause"], d["detected_by"])),
    WatchValues: _map("registers.watch",
                      lambda e: {"sub_id": e.sub_id, "pos": e.position, "ts": e.ts,
                                 "values": [{"name": n, "value": v} for n, v in e.values.items()]},
                      lambda d: WatchValues(d["sub_id"], d["pos"], d["ts"],
                                            {v["name"]: v["value"] for v in d["values"]})),
    ActivityProgress: _map("activity.progress", _progress_to_wire, _progress_from_wire),
    ActivityFinished: _map("activity.finished", _finished_to_wire, _finished_from_wire),
    LogLine: _map("log.line",
                  lambda e: _drop_empty({"ts": e.ts, "level": e.level, "source": e.source, "text": e.text,
                                         "pos": e.position}, "pos"),
                  lambda d: LogLine(d["ts"], d["level"], d["source"], d["text"], d.get("pos"))),
    CallLate: _map("call.late", _late_to_wire,
                   lambda d: CallLate(d["request_id"], d["ok"], d.get("result"), d.get("error"))),
}
NAMES: Dict[type, str] = {cls: spec.name for cls, spec in EVENTS.items()}
BY_NAME: Dict[str, type] = {spec.name: cls for cls, spec in EVENTS.items()}
assert set(BY_NAME) == set(BY_EVENT), "every protocol event has an app event, and no more"


def encode_event(event: GatewayEvent) -> Tuple[str, Any]:
    """The notification name and data for an event. Raises KeyError for a type that has no wire name."""
    spec = EVENTS[type(event)]
    return spec.name, spec.to_wire(event)


def decode_event(name: str, data: Any) -> GatewayEvent:
    """The event for a notification. Raises KeyError for an unknown name and CodecError for bad data."""
    spec = EVENTS[BY_NAME[name]]
    return spec.from_wire(decode(spec.data, data))
