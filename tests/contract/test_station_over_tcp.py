"""The station over the real wire: requests by their protocol names, replies and events checked against the
protocol's types (conftest.Station).

Each area gets a few calls, plus the things only the wire can get wrong: error codes and data, events, the
timeout / call.late pair, bad frames, and parameter ranges.
"""

import base64
import dataclasses
import socket
import struct

import pytest

from station_protocol.errors import ErrorCode
from station_protocol.framing import FrameReader, decode_body, encode_frame

REG = "BUFC.LPMODE"


# ---- sys and dut ------------------------------------------------------------------------------------------

def test_hello_status_and_connect(station):
    hello = station.call("sys.hello", client="conformance", protocol=2)
    assert hello["release_id"] and hello["protocol"] == 2
    result = station.call("dut.connect", pos=1, config_type="EFR32", config_file="")
    assert result.chip.part and result.rpc is not None
    status = station.call("sys.status")
    assert [p.dut_connected for p in status.positions] == [True, False, False, False]
    station.pump(lambda: station.of("status.changed") and station.of("log.line"))


def test_wrong_state_keeps_its_code_and_missing_tags(station):
    error = station.error("registers.read", pos=1, name="CMU.CTRL")
    assert error.code == ErrorCode.WRONG_STATE and error.data["missing"] == ["dut"]


def test_load_phy_takes_the_tagged_phy(connected):
    result = connected.call("dut.load_phy", pos=1, phy={"kind": "lpw", "name": "BLE_1M"})
    assert result.name == "BLE_1M"
    assert connected.call("sys.status").positions[0].phy == "BLE_1M"


# ---- registers ----------------------------------------------------------------------------------------------

def test_tree_read_and_write(connected):
    tree = connected.call("registers.tree", pos=1)
    assert tree["tree_id"] and tree["peripherals"] and all(p["registers"] for p in tree["peripherals"])
    written = connected.call("registers.write", pos=1, name=REG, value=1)
    assert written.value_written == 1 and written.verified
    assert connected.call("registers.read", pos=1, name=REG) == 1


def test_errors_inside_read_many_come_back_per_register(connected):
    items = connected.call("registers.read_many", pos=1, names=[REG, "NOPE.REG"])
    assert items[0].value is not None and items[1].error is not None
    assert items[1].error.code == ErrorCode.NOT_FOUND


def test_a_critical_write_needs_confirm(connected):
    tree = connected.call("registers.tree", pos=1)
    critical = next(f"{p['name']}.{r['name']}" for p in tree["peripherals"] if p["critical"]
                    for r in p["registers"] if r["access"].value in ("rw", "wo", "w1", "rw1"))
    error = connected.error("registers.write", pos=1, name=critical, value=0)
    assert error.code == ErrorCode.CONFIRMATION_REQUIRED


def test_watch_values_arrive_as_events(connected):
    sub_id = connected.call("registers.watch", pos=1, names=[REG], interval_s=0.1)
    connected.pump(lambda: any(e["sub_id"] == sub_id for e in connected.of("registers.watch")))
    tick = connected.of("registers.watch")[-1]
    assert tick["pos"] == 1 and [v["name"] for v in tick["values"]] == [REG]
    connected.call("registers.unwatch", sub_id=sub_id)


# ---- activities, instruments, rf, memory, advanced, tests ----------------------------------------------------

def _finished(station, activity_id, timeout=5.0):
    station.pump(lambda: any(e["activity_id"] == activity_id for e in station.of("activity.finished")), timeout)
    return [e for e in station.of("activity.finished") if e["activity_id"] == activity_id][0]


def test_a_sequence_reports_progress_and_finishes(connected):
    ops = [{"type": "register_write", "register": REG, "value": 0, "group": "lpmode_off"}]
    activity_id = connected.call("automation.seq.run", pos=1, ops=ops)
    finished = _finished(connected, activity_id)
    assert any(e["activity_id"] == activity_id for e in connected.of("activity.progress"))
    assert finished["ok"] and finished["pos"] == 1 and "instrument_id" not in finished


def test_malformed_ops_are_refused_before_the_run_starts(connected):
    for ops in ([{"register": REG, "value": 0}],                       # no type
                [{"type": "register_write", "register": REG}],         # no value
                [{"type": "sequence", "sequence_name": "s"}],          # never sent by a client
                []):
        error = connected.error("automation.seq.run", pos=1, ops=ops)
        assert error.code == ErrorCode.INVALID_PARAMS and error.data["param"].startswith("ops")
    assert connected.call("sys.status").positions[0].activity == "idle"


def test_an_eca_capture_comes_back_as_base64_pages(station):
    sources = station.call("instruments.eca.sources", id="eca1")
    spec = {"channels": [sources.channels[0]], "trigger": "immediate", "duration_s": 0.001}
    activity_id = station.call("instruments.eca.capture", id="eca1", spec=spec)
    finished = _finished(station, activity_id, timeout=10)
    assert finished["instrument_id"] == "eca1" and "pos" not in finished
    page = station.call("instruments.eca.result", capture_id=finished["result"]["capture_id"])
    samples = base64.b64decode(page.channels[sources.channels[0]])
    assert page.count == len(samples) // 2 and page.meta.spec.channels == (sources.channels[0],)


def test_instrument_rf_memory_console_and_tests(connected):
    c = connected.call
    assert c("rf.paths")
    config = c("instruments.siggen.get", id="siggen1")
    c("instruments.siggen.set", id="siggen1", config=dataclasses.asdict(config))   # what was read, sent back
    assert c("instruments.chamber.read", id="chamber1").target_c is not None
    c("rf.prs_route", pos=1, route={"signal": "FRAMEDET", "pin": "PA0", "channel": 0})
    block = c("memory.read", pos=1, address=0x20000000, size=16)
    assert len(base64.b64decode(block.data)) == 16
    session = c("advanced.console.open", pos=1)
    assert c("advanced.console.exec", session_id=session, code="1 + 2").result_text == "3"
    c("advanced.console.close", session_id=session)
    tests = c("tests.list")
    assert tests and tests[0].id


def test_an_unknown_instrument_is_not_found(station):
    assert station.error("instruments.siggen.get", id="siggen9").code == ErrorCode.NOT_FOUND


# ---- timeouts and late results ------------------------------------------------------------------------------

def test_a_timeout_then_call_late_carry_the_json_rpc_id(connected):
    connected.on_fake(lambda f: f.time_out_next("registers.write", late_ms=200))
    error = connected.error("registers.write", pos=1, name=REG, value=1)
    assert error.code == ErrorCode.TIMEOUT and error.data["still_running"] is True
    connected.pump(lambda: connected.of("call.late"))
    late = connected.of("call.late")[0]
    assert late["request_id"] == error.data["request_id"] and late["ok"]
    assert late["result"]["value_written"] == 1   # in registers.write's result shape


def test_a_slow_call_times_out_at_timeout_ms_and_its_result_comes_later(connected):
    connected.on_fake(lambda f: f.set_latency("registers.read", 600))
    box = connected.send("registers.read", timeout_ms=200, pos=1, name=REG)
    connected.pump(lambda: box)
    error = box[0][1]
    assert error is not None and error.code == ErrorCode.TIMEOUT and error.data["still_running"] is True
    assert not error.data.get("client_side")   # the station answered the timeout, not the client
    connected.pump(lambda: connected.of("call.late"))
    late = connected.of("call.late")[0]
    assert late["request_id"] == error.data["request_id"] and late["ok"] and isinstance(late["result"]["value"], int)


def test_a_dropped_dut_arrives_as_an_event(connected):
    connected.on_fake(lambda f: f.drop_dut(1))
    connected.pump(lambda: connected.of("dut.disconnected"))
    assert connected.of("dut.disconnected")[0]["pos"] == 1


# ---- topics -------------------------------------------------------------------------------------------------

def test_events_only_come_for_subscribed_topics(make_station):
    station = make_station(subscribe=False)
    station.call("dut.connect", pos=1, config_type="EFR32", config_file="")
    assert station.events == []   # nothing subscribed, nothing sent
    station.subscribe(["log"])
    station.call("dut.disconnect", pos=1)   # changes the status and logs
    station.call("dut.connect", pos=1, config_type="EFR32", config_file="")
    station.pump(lambda: station.of("log.line"))
    assert not station.of("dut.disconnected") and not station.of("status.changed")
    station.call("dut.disconnect", pos=1)


def test_an_unknown_topic_is_refused(station):
    error = station.error("sys.subscribe", topics=["status", "weather"])
    assert error.code == ErrorCode.INVALID_PARAMS and "weather" in error.message


# ---- what a client leaves behind ----------------------------------------------------------------------------

def test_a_client_that_goes_away_ends_its_watches_and_console_sessions(connected):
    sub_id = connected.call("registers.watch", pos=1, names=[REG], interval_s=1.0)
    session = connected.call("advanced.console.open", pos=1)
    assert connected.on_fake(lambda f: sub_id in f.fake_registers.watches)
    connected.link.close()
    connected.pump(lambda: connected.on_fake(lambda f: not f.fake_registers.watches))
    assert connected.on_fake(lambda f: f.facts[1].watching) is False
    assert connected.on_fake(lambda f: session not in f.advanced.sessions)


# ---- the wire's own failures --------------------------------------------------------------------------------

def _raw(station):
    """A raw socket to the station, for sending what a client never would."""
    sock = socket.create_connection(station.address, timeout=5)
    reader = FrameReader()

    def receive():
        while True:
            for body in reader.feed(sock.recv(65536)):
                message = decode_body(body)
                if "id" in message:   # skip events
                    return message
    return sock, receive


def test_bad_messages_get_json_rpc_errors(station):
    sock, receive = _raw(station)
    try:
        sock.sendall(struct.pack(">I", 5) + b"{nope")
        assert receive()["error"]["code"] == -32700
        sock.sendall(encode_frame([{"jsonrpc": "2.0", "id": 1, "method": "sys.status"}]))
        assert receive()["error"]["code"] == -32600
        sock.sendall(encode_frame({"jsonrpc": "2.0", "id": 2, "method": "sys.nope", "params": {}}))
        assert receive()["error"] == {"code": -32601, "message": "Unknown method sys.nope",
                                      "data": {"reason": "unknown_method"}}
        sock.sendall(encode_frame({"jsonrpc": "2.0", "id": 3, "method": "registers.read", "params": {"pos": "x"}}))
        reply = receive()
        assert reply["id"] == 3 and reply["error"]["data"]["reason"] == "invalid_params"
        sock.sendall(encode_frame({"jsonrpc": "2.0", "id": 4, "method": "sys.status", "params": {"extra": 1}}))
        assert receive()["error"]["data"] == {"reason": "invalid_params", "param": "extra"}
    finally:
        sock.close()


def test_an_oversized_frame_closes_the_connection(station):
    sock, _ = _raw(station)
    try:
        sock.sendall(struct.pack(">I", 17 * 1024 * 1024))
        sock.settimeout(5)
        assert sock.recv(1) == b""   # the station hung up
    finally:
        sock.close()


# ---- parameter ranges, checked when the station validates params (station_protocol) ----------------------------

@pytest.mark.parametrize("method, params, param", [
    ("registers.read", {"pos": 9, "name": REG}, "pos"),
    ("registers.watch", {"pos": 1, "names": [REG], "interval_s": 0.01}, "interval_s"),
    ("memory.read", {"pos": 1, "address": 0x20000000, "size": 5000}, "size"),
    ("memory.write", {"pos": 1, "address": 0x20000000, "value": 1, "size": 3}, "size"),
    ("dut.connect", {"pos": 1, "config_type": "ARM", "config_file": ""}, "config_type"),
    ("dut.set_rpc_timeout", {"seconds": 0.5}, "seconds"),
    ("instruments.siggen.trigger", {"id": "siggen1", "mode": "twice"}, "mode"),
], ids=["pos", "interval", "read size", "write size", "config type", "rpc timeout", "trigger mode"])
def test_out_of_range_parameters_are_refused_at_the_edge(connected, method, params, param):
    error = connected.error(method, **params)
    assert error.code == ErrorCode.INVALID_PARAMS and error.data["param"] == param
