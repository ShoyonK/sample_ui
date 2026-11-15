"""The protocol package on its own (station_protocol): frames, the JSON-RPC 2.0 envelope, validation, and the
method catalog. Nothing here uses an application."""

import json

import pytest

from station_protocol import PROTOCOL_VERSION, jsonrpc
from station_protocol.catalog import BY_EVENT, BY_WIRE, EVENTS, METHODS, TOPICS
from station_protocol.common import PositionFacts
from station_protocol.errors import ApiError, ErrorCode
from station_protocol.framing import MAX_FRAME, FrameError, FrameReader, decode_body, encode_frame
from station_protocol.method import check_params, read_result, wrap_result
from station_protocol.validate import ValidationFailed, validate


def _json(value):
    """Through real JSON text, as on the wire."""
    return json.loads(json.dumps(value))


# ---- frames -----------------------------------------------------------------------------------------------

def test_frames_come_out_whole_however_the_bytes_are_split():
    data = encode_frame({"a": 1}) + encode_frame({"b": "é"})
    reader = FrameReader()
    bodies = [body for i in range(len(data)) for body in reader.feed(data[i:i + 1])]   # one byte at a time
    assert [decode_body(b) for b in bodies] == [{"a": 1}, {"b": "é"}]
    assert [decode_body(b) for b in FrameReader().feed(data)] == [{"a": 1}, {"b": "é"}]   # both in one read


def test_an_oversized_frame_is_refused_before_its_body_is_read():
    header = (MAX_FRAME + 1).to_bytes(4, "big")
    with pytest.raises(FrameError):
        FrameReader().feed(header)
    with pytest.raises(FrameError):
        encode_frame("x" * (MAX_FRAME + 1))


def test_a_body_that_isnt_json_is_a_frame_error():
    with pytest.raises(FrameError):
        decode_body(b"{nope")


# ---- envelope ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("code", list(ErrorCode))
def test_every_error_code_survives_the_round_trip(code):
    error = ApiError(code, "it went wrong", {"missing": ["dut"]})
    obj = _json(jsonrpc.error_object(error))
    assert isinstance(obj["code"], int) and obj["data"]["reason"] == code.value
    back = jsonrpc.api_error(obj)
    assert (back.code, back.message, back.data) == (code, "it went wrong", {"missing": ["dut"]})


def test_an_error_without_a_reason_is_read_by_its_number():
    assert jsonrpc.api_error({"code": -32001, "message": "x"}).code == ErrorCode.WRONG_STATE
    assert jsonrpc.api_error({"code": -32601, "message": "x"}).code == ErrorCode.UNKNOWN_METHOD
    assert jsonrpc.api_error({"code": 12345, "message": "x"}).code == ErrorCode.INTERNAL


def test_requests_carry_the_version_named_params_and_the_timeout_in_meta():
    message = jsonrpc.request(7, "registers.read", {"pos": 1, "name": "A.B"}, 5000)
    assert message == {"jsonrpc": "2.0", "id": 7, "method": "registers.read",
                       "params": {"pos": 1, "name": "A.B", "_meta": {"timeout_ms": 5000}}}
    request = jsonrpc.read_request(_json(message))
    assert (request.id, request.params, request.timeout_ms) == (7, {"pos": 1, "name": "A.B"}, 5000)


@pytest.mark.parametrize("message, code", [
    ([{"jsonrpc": "2.0", "id": 1, "method": "sys.status"}], jsonrpc.INVALID_REQUEST),   # a batch
    ({"id": 1, "method": "sys.status"}, jsonrpc.INVALID_REQUEST),                      # no version
    ({"jsonrpc": "2.0", "id": 1}, jsonrpc.INVALID_REQUEST),                            # no method
    ({"jsonrpc": "2.0", "id": 1, "method": "sys.status", "params": [1]}, -32602),     # positional params
])
def test_invalid_requests_are_refused_with_the_right_code(message, code):
    with pytest.raises(jsonrpc.ProtocolError) as caught:
        jsonrpc.read_request(message)
    assert caught.value.code == code


def test_the_client_reads_replies_errors_and_notifications():
    assert jsonrpc.read_incoming(jsonrpc.reply(3, {"x": 1})) == jsonrpc.Reply(3, {"x": 1})
    error = jsonrpc.read_incoming(jsonrpc.error_reply(4, jsonrpc.error_object(ApiError(ErrorCode.BUSY, "b"))))
    assert isinstance(error, jsonrpc.Reply) and error.error is not None and error.error.code == ErrorCode.BUSY
    note = jsonrpc.read_incoming(jsonrpc.notification("log.line", 9, {"text": "hi"}))
    assert note == jsonrpc.Notification("log.line", 9, {"text": "hi"})


# ---- validation -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("data, message", [
    ({"position": "one"}, "position: must be a whole number"),
    ({}, "position: is required"),
    ({"position": 1, "watching": 1}, "watching: must be true or false"),
])
def test_json_that_doesnt_fit_says_where(data, message):
    with pytest.raises(ValidationFailed, match=message):
        validate(PositionFacts, data)


def test_unknown_fields_from_a_newer_peer_are_ignored():
    assert validate(PositionFacts, {"position": 2, "battery": "low"}) == PositionFacts(2)


def test_a_phy_is_tagged_by_kind():
    phy = BY_WIRE["dut.load_phy"].params[1].type
    assert validate(phy, {"kind": "lpw", "name": "BLE_1M"}) == {"kind": "lpw", "name": "BLE_1M"}
    with pytest.raises(ValidationFailed, match="kind must be one of"):
        validate(phy, {"kind": "zigbee", "name": "x"})


# ---- the catalog ----------------------------------------------------------------------------------------------

def test_every_method_has_a_unique_name_and_a_known_group():
    assert len(BY_WIRE) == len(METHODS)
    assert {m.group for m in METHODS} == {"sys", "dut", "rf", "registers", "activity", "automation", "tests",
                                          "instruments", "memory", "advanced"}


def test_every_event_has_a_known_topic_or_goes_to_the_caller():
    assert {e.topic for e in EVENTS} == set(TOPICS) | {None}
    assert BY_EVENT["call.late"].topic is None


def test_hello_says_who_is_calling_and_which_protocol():
    hello = BY_WIRE["sys.hello"]
    assert [(p.wire, p.required) for p in hello.params] == [("client", True), ("protocol", True)]
    assert PROTOCOL_VERSION == 2


def test_params_are_checked_with_defaults_filled_in():
    write = BY_WIRE["registers.write"]
    assert check_params(write, {"pos": 1, "name": "A.B", "value": 3}) == {
        "pos": 1, "name": "A.B", "value": 3, "confirm": False, "verify": True}


@pytest.mark.parametrize("params, param", [
    ({"pos": 1, "name": "A.B", "value": 3, "extra": 1}, "extra"),      # unknown
    ({"pos": 1, "name": "A.B"}, "value"),                              # missing
    ({"pos": 9, "name": "A.B", "value": 3}, "pos"),                    # out of range
    ({"pos": 1, "name": "A.B", "value": "3"}, "value"),                # "3" is not 3
])
def test_bad_params_are_invalid_params_naming_the_param(params, param):
    with pytest.raises(ApiError) as caught:
        check_params(BY_WIRE["registers.write"], params)
    assert caught.value.code == ErrorCode.INVALID_PARAMS and caught.value.data["param"] == param


def test_results_are_objects_and_empty_is_an_empty_object():
    assert wrap_result(BY_WIRE["registers.read"], 3) == {"value": 3}
    assert wrap_result(BY_WIRE["automation.seq.run"], "a1") == {"activity_id": "a1"}
    assert wrap_result(BY_WIRE["sys.subscribe"], None) == {}
    assert wrap_result(BY_WIRE["tests.list"], []) == {"tests": []}
    assert read_result(BY_WIRE["registers.read"], {"value": 3}) == 3
    with pytest.raises(ValidationFailed):
        read_result(BY_WIRE["registers.read"], 3)   # a bare value isn't a result

