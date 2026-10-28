"""Real request and response payloads, captured by calling every gateway method on the fake station.

The fake is the frontend's reference implementation of the API (it enforces the same requires and returns the
same error codes), so what it answers is what the GUI is built to consume. capture() returns, per API method:
{"params": wire params, "result" | "error": payload, "events": [wire events the call caused]}.

Run from the repo root:  uv run python scripts/architecture/payloads.py   (prints JSON)
"""

from __future__ import annotations

import base64
import dataclasses
import enum
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sirat_ui.core.wifi import WifiSettings  # noqa: E402
from sirat_ui.gateway.errors import ApiError  # noqa: E402
from sirat_ui.gateway.fake.fake_station import FakeStationGateway  # noqa: E402
from sirat_ui.gateway.scheduler import ManualScheduler  # noqa: E402
from sirat_ui.models.station import (ActivityFinished, ActivityProgress, CallLate, CaptureSpec,  # noqa: E402
                                     DutDisconnected, LogLine, LpwPhy, PrsRoute, RpcAddress, SiggenConfig,
                                     StatusChanged, WatchValues, WifiPhy)


def wire(value: Any) -> Any:
    """Dataclasses, enums, tuples, bytes and errors as JSON."""
    if isinstance(value, ApiError):
        return {"code": value.code.value, "message": value.message, "data": wire(value.data)}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: wire(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [wire(v) for v in value]
    if isinstance(value, dict):
        return {str(k): wire(v) for k, v in value.items()}
    if isinstance(value, bytes):
        return base64.b64encode(value).decode()
    return value


def wire_event(event: Any) -> Dict[str, Any]:
    """The API's event names and field names (docs/API_DESIGN.md section 7) for the client's event models."""
    if isinstance(event, StatusChanged):
        return {"event": "status.changed", "data": wire(event.status)}
    if isinstance(event, ActivityProgress):
        data = {"activity_id": event.activity_id, "step": event.step, "total": event.total, "message": event.message}
        data.update({"pos": event.position} if event.position else {"instrument_id": event.instrument_id})
        if event.group:
            data["group"] = event.group
        return {"event": "activity.progress", "data": data}
    if isinstance(event, ActivityFinished):
        data = {"activity_id": event.activity_id, "ok": event.ok, "results": wire(event.results)}
        data.update({"pos": event.position} if event.position else {"instrument_id": event.instrument_id})
        if event.result is not None:
            data["result"] = wire(event.result)
        if event.error is not None:
            data["error"] = wire(event.error)
        return {"event": "activity.finished", "data": data}
    if isinstance(event, WatchValues):
        return {"event": "registers.watch", "data": {"sub_id": event.sub_id, "pos": event.position, "ts": event.ts,
                                                      "values": [{"name": k, "value": v} for k, v in event.values.items()]}}
    if isinstance(event, DutDisconnected):
        return {"event": "dut.disconnected", "data": {"pos": event.position, "cause": event.cause,
                                                       "detected_by": event.detected_by}}
    if isinstance(event, LogLine):
        data = {"ts": event.ts, "level": event.level, "source": event.source, "text": event.text}
        if event.position is not None:
            data["pos"] = event.position
        return {"event": "log.line", "data": data}
    if isinstance(event, CallLate):
        data = {"request_id": event.request_id, "ok": event.ok}
        data.update({"result": wire(event.result)} if event.ok else {"error": wire(event.error)})
        return {"event": "call.late", "data": data}
    return {"event": type(event).__name__, "data": wire(event)}


def wire_params(position, params: Dict[str, Any]) -> Dict[str, Any]:
    out = {} if position is None else {"pos": position}
    for k, v in params.items():
        if k == "phy":   # PhySpec is tagged by "kind" on the wire
            v = {"kind": "lpw", "name": v.name} if isinstance(v, LpwPhy) else {"kind": "wifi", "config": v.config.to_dict()}
        out[k] = wire(v)
    return out


def capture() -> Dict[str, Dict[str, Any]]:
    scheduler = ManualScheduler()
    fake = FakeStationGateway(scheduler, clock=lambda: 1793200000.0)
    events: List[Any] = []
    fake.events.connect(events.append)
    out: Dict[str, Dict[str, Any]] = {}

    def run(fn, advance_ms: int = 0) -> Any:
        before_calls, before_events = len(fake.calls), len(events)
        box: Dict[str, Any] = {}
        fn().then(lambda r: box.setdefault("result", r), lambda e: box.setdefault("error", e))
        if advance_ms:
            scheduler.advance(advance_ms)
        rec = fake.calls[before_calls]
        entry = {"params": wire_params(rec.position, rec.params)}
        if "error" in box:
            entry["error"] = wire(box["error"])
        else:
            entry["result"] = wire(box.get("result"))
        entry["events"] = [wire_event(e) for e in events[before_events:]]
        out.setdefault(rec.method, entry)
        return box.get("result")

    run(lambda: fake.hello())
    run(lambda: fake.subscribe(["status", "activity", "watch", "instrument", "log"]))
    run(lambda: fake.connect_dut(1, "EFR32", ""))
    run(lambda: fake.status())
    run(lambda: fake.probe(1, RpcAddress("10.0.0.12", 10001), 2.0))
    run(lambda: fake.dut_info(1))
    run(lambda: fake.set_rpc_timeout(10))
    run(lambda: fake.load_phy(1, LpwPhy("BLE_1M")))
    wifi = WifiSettings(standard="802.11ax", channel=36, power_mode="HP").normalized().config()
    family = fake.chip
    fake.chip = dataclasses.replace(fake.chip, family="EVEREST")   # WiFi PHYs need an Everest DUT
    out["dut.load_phy (wifi)"] = _call(fake, events, lambda: fake.load_phy(1, WifiPhy(wifi)))
    fake.chip = family
    run(lambda: fake.register_tree(1))
    reg = next(r for p in fake.peripherals if p.name == "BUFC" for r in p.registers if r.name == "LPMODE")
    run(lambda: fake.read_register(1, reg.full_name))
    run(lambda: fake.read_many(1, [reg.full_name, "USART0.RXDATA", "NOPE.REG"]))
    run(lambda: fake.write_register(1, reg.full_name, 3))
    run(lambda: fake.write_field(1, reg.full_name, reg.fields[0].name, 1))
    sub = run(lambda: fake.watch(1, [reg.full_name, "SYNTH.FREQ"], 1.0))
    before_events = len(events)
    scheduler.advance(1000)
    out["registers.watch"]["events"] = [wire_event(e) for e in events[before_events:]]
    run(lambda: fake.unwatch(sub))
    run(lambda: fake.memory_read(1, 0x20000000, 32))
    run(lambda: fake.memory_write(1, 0x20000010, 0xCAFEF00D, 4))
    run(lambda: fake.rf_paths())
    run(lambda: fake.rf_connect(1, "TX_PATH"))
    run(lambda: fake.rf_disconnect(1))
    run(lambda: fake.prs_signals(1))
    run(lambda: fake.prs_route(1, PrsRoute("RAC_RX", "PC0", 6)))
    run(lambda: fake.list_instruments())
    run(lambda: fake.connect_instrument("siggen1"))
    run(lambda: fake.siggen_get("siggen1"))
    run(lambda: fake.siggen_set("siggen1", SiggenConfig("PacketSrw", "BLE_1M", 2402e6, -10.0, {"GAIN": 3})))
    run(lambda: fake.siggen_waveforms("siggen1"))
    run(lambda: fake.siggen_trigger("siggen1", "single"))
    run(lambda: fake.siggen_rf("siggen1", True))
    run(lambda: fake.chamber_read("chamber1"))
    run(lambda: fake.chamber_set_temp("chamber1", 40.0))
    run(lambda: fake.chamber_wait_stable("chamber1", 0.5, 2), advance_ms=12000)
    run(lambda: fake.eca_sources("eca1"))
    capture_id = None
    before = len(events)
    run(lambda: fake.eca_capture("eca1", CaptureSpec(("PA_EN", "RX_EN"), "PA_EN", "rising", 1e6, 0.004, 10)),
        advance_ms=2000)
    for e in events[before:]:
        if isinstance(e, ActivityFinished) and e.result:
            capture_id = e.result["capture_id"]
    run(lambda: fake.eca_result(capture_id, 0, 4))
    sid = run(lambda: fake.console_open(1))
    run(lambda: fake.console_exec(sid, "x = 6 * 7"))
    out["advanced.console.exec (value)"] = _call(fake, events, lambda: fake.console_exec(sid, "x"))
    out["advanced.console.exec (error)"] = _call(fake, events, lambda: fake.console_exec(sid, "1/0"))
    run(lambda: fake.console_names(sid))
    run(lambda: fake.custom_function(1, "read_rssi", "rssi = dut.rta.lpw.GetRSSI()\nprint(rssi)\nreturn rssi", sid))
    run(lambda: fake.console_close(sid))
    run(lambda: fake.dut_control_describe(1))
    run(lambda: fake.dut_control_invoke(1, "lpw.radio.SetPower", [], {"power_dbm": 10.5}))
    out["advanced.dut_control.invoke (error)"] = _call(
        fake, events, lambda: fake.dut_control_invoke(1, "lpw.radio.SetPower", [], {"power_dbm": 30}))
    ops = [{"type": "register_write", "register": reg.full_name, "value": 1, "group": "lpmode_on"},
           {"type": "dut_control_method", "method_path": "lpw.radio.SetChannel", "method_name": "SetChannel",
            "params": {"channel": 5}, "group": "set_channel"}]
    run(lambda: fake.run_sequence(1, ops, True), advance_ms=2000)
    act = run(lambda: fake.run_sequence(1, ops, True))
    run(lambda: fake.abort_activity(act), advance_ms=2000)
    run(lambda: fake.recover(1))
    fake.time_out_next("registers.write", late_ms=1500)
    out["registers.write (timeout)"] = _call(fake, events, lambda: fake.write_register(1, reg.full_name, 1), 2000)
    out["registers.write (critical, no confirm)"] = _call(
        fake, events, lambda: fake.write_register(1, "CMU.CLKEN0", 1))
    before_events = len(events)
    fake.drop_dut(1)
    out["(event) dut.disconnected"] = {"events": [wire_event(e) for e in events[before_events:]]}
    out["registers.read (no DUT)"] = _call(fake, events, lambda: fake.read_register(1, reg.full_name))
    run(lambda: fake.disconnect_dut(1))
    out["dut.reconnect"] = _call(fake, events, lambda: fake.reconnect_dut(1))
    return out


def _call(fake, events, fn, advance_ms: int = 0) -> Dict[str, Any]:
    before_calls, before_events = len(fake.calls), len(events)
    box: Dict[str, Any] = {}
    fn().then(lambda r: box.setdefault("result", r), lambda e: box.setdefault("error", e))
    if advance_ms:
        fake.scheduler.advance(advance_ms)
    rec = fake.calls[before_calls]
    entry = {"params": wire_params(rec.position, rec.params)}
    entry.update({"error": wire(box["error"])} if "error" in box else {"result": wire(box.get("result"))})
    entry["events"] = [wire_event(e) for e in events[before_events:]]
    return entry


if __name__ == "__main__":
    print(json.dumps(capture(), indent=1, default=str))
