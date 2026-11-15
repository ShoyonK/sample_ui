"""The app's side of the wire (gateway/wire): the model codec, the event table and the gateway bindings, against
the protocol they map to (station_protocol)."""

import dataclasses
import enum
import inspect
import json
from typing import List

import pytest

from station_protocol import advanced, common, dut, instruments, memory, registers, rf
from station_protocol import tests as station_tests
from station_protocol.catalog import BY_WIRE
from station_protocol.registers import RegisterTree
from sibench_ui.gateway.api.client import ApiStationGateway
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.fake.chip import build_chip
from sibench_ui.gateway.fake.fake_station import FakeStationGateway
from sibench_ui.gateway.port import CLIENT, PROTOCOL, StationGateway
from sibench_ui.gateway.wire.bindings import BY_ATTR, BY_WIRE_NAME
from sibench_ui.gateway.wire.codec import CodecError, decode, encode, to_wire
from sibench_ui.gateway.wire.events import BY_NAME, decode_event, encode_event
from sibench_ui.models import facts, radio
from sibench_ui.models import registers as app_registers
from sibench_ui.models import station as app_station
from sibench_ui.models.radio import WifiAdvanced, WifiPhyConfig, WifiTxParams
from sibench_ui.models.registers import PeripheralDef
from sibench_ui.models.station import (ActivityFinished, ActivityProgress, CallLate, DutDisconnected, LogLine,
                                     LpwPhy, PhySpec, ReadManyItem, StationStatus, StatusChanged, WatchValues,
                                     WifiPhy)
from sibench_ui.models.facts import PositionFacts


def _json(value):
    """Through real JSON text, as on the wire."""
    return json.loads(json.dumps(value))


# ---- codec ------------------------------------------------------------------------------------------------

def test_the_register_tree_round_trips():
    chip = build_chip()
    assert decode(List[PeripheralDef], _json(to_wire(List[PeripheralDef], chip))) == chip


def test_phy_specs_are_tagged_by_kind():
    wifi = WifiPhy(WifiPhyConfig("TX", "802.11ax", 36, "MP", "MCS7", "WIFI_5G", WifiTxParams(100, 0, "burst", True),
                                 WifiAdvanced("SU", "1x_0.8", False, "20MHz")))
    assert encode(LpwPhy("BLE_1M")) == {"kind": "lpw", "name": "BLE_1M"}
    assert decode(PhySpec, _json(encode(wifi))) == wifi
    with pytest.raises(CodecError):
        decode(PhySpec, {"kind": "zigbee", "name": "x"})


def test_an_error_inside_a_result_keeps_its_code_and_data():
    item = ReadManyItem("UART0.RXDATA", error=ApiError(ErrorCode.READ_SENSITIVE, "no", {"register": "UART0.RXDATA"}))
    back = decode(ReadManyItem, _json(encode(item)))
    assert back.error is not None and (back.error.code, back.error.data) == (ErrorCode.READ_SENSITIVE,
                                                                             {"register": "UART0.RXDATA"})


@pytest.mark.parametrize("data, message", [
    ({"position": "one"}, "position: must be a whole number"),
    ({}, "position: is required"),
    ({"position": 1, "watching": 1}, "watching: must be true or false"),
])
def test_json_that_doesnt_fit_says_where(data, message):
    with pytest.raises(CodecError, match=message):
        decode(PositionFacts, data)


def test_unknown_fields_from_a_newer_station_are_ignored():
    assert decode(PositionFacts, {"position": 2, "battery": "low"}) == PositionFacts(2)


@pytest.mark.parametrize("event", [
    StatusChanged(StationStatus("r1", [PositionFacts(1, True, "BLE_1M")])),
    DutDisconnected(2, "RPC connection lost", "heartbeat"),
    WatchValues("w1", 1, 12.5, {"CMU.CLKEN0": 3, "GPIO.PA_DOUT": 0}),
    ActivityProgress("a1", 1, 2, 5, "Writing", group="setup"),
    ActivityFinished("a1", 1, False, [{"ok": True}], ApiError(ErrorCode.ABORTED, "Aborted by user")),
    LogLine(1.0, "info", "station", "hello", 3),
    CallLate(17, True, {"value_written": 1}),
])
def test_every_event_round_trips(event):
    name, data = encode_event(event)
    back = decode_event(name, _json(data))
    if isinstance(event, ActivityFinished):
        assert back.error is not None and back.error.code == ErrorCode.ABORTED   # ApiError has no __eq__
        back.error = event.error
    assert back == event


def test_events_write_the_position_as_pos_and_watch_values_as_a_list():
    assert encode_event(DutDisconnected(2, "c", "d"))[1] == {"pos": 2, "cause": "c", "detected_by": "d"}
    assert encode_event(WatchValues("w1", 1, 0.0, {"A.B": 3}))[1]["values"] == [{"name": "A.B", "value": 3}]


def test_every_gateway_event_type_has_a_wire_name():
    from sibench_ui.models.station import GatewayEvent
    assert set(GatewayEvent.__args__) == set(BY_NAME.values())   # type: ignore[attr-defined]


# ---- the bindings ---------------------------------------------------------------------------------------------

def _gateway_methods():
    """Every method StationGateway declares (gateway/port.py)."""
    names = set()
    for cls in StationGateway.__mro__:
        if cls.__module__ == "sibench_ui.gateway.port":
            names |= {n for n, v in vars(cls).items() if inspect.isfunction(v) and not n.startswith("_")}
    return names


def test_the_bindings_cover_the_station_gateway_and_the_protocol_exactly():
    assert set(BY_ATTR) == _gateway_methods()
    assert set(BY_WIRE_NAME) == set(BY_WIRE)


@pytest.mark.parametrize("binding", BY_ATTR.values(), ids=lambda b: b.method.wire)
def test_parameters_match_both_backends(binding):
    """The gateway's parameters, in the protocol's order, on the client and on the fake."""
    expected = [name for name, _ in binding.args]
    for backend in (ApiStationGateway, FakeStationGateway):
        params = list(inspect.signature(getattr(backend, binding.attr)).parameters)[1:]
        assert params == expected, f"{backend.__name__}.{binding.attr}"


def test_the_server_answers_in_the_protocols_result_shapes():
    from sibench_ui.gateway.fake.server import FakeStationServer
    result = FakeStationServer._result
    assert result(BY_WIRE_NAME["registers.read"], 3) == {"value": 3}
    assert result(BY_WIRE_NAME["automation.seq.run"], "a1") == {"activity_id": "a1"}
    assert result(BY_WIRE_NAME["sys.subscribe"], None) == {}
    assert result(BY_WIRE_NAME["tests.list"], []) == {"tests": []}


def test_the_register_tree_travels_in_the_contracts_shape_and_round_trips():
    from sibench_ui.gateway.wire.shapes import tree_from_wire, tree_to_wire
    chip = build_chip()
    wire = _json(tree_to_wire(chip))
    peripheral = wire["peripherals"][0]
    assert wire["tree_id"].startswith("sha256:") and {"critical", "read_sensitive"} <= set(peripheral)
    register = peripheral["registers"][0]
    assert "reset_value" in register and "peripheral" not in register and "register" not in register["fields"][0]
    assert tree_from_wire(decode(RegisterTree, wire)) == chip


def test_an_activity_carries_its_position_or_its_instrument_not_both():
    on_dut = encode_event(ActivityProgress("a1", 1, 1, 2, "Writing"))[1]
    on_instrument = encode_event(ActivityProgress("a2", 0, 1, 2, "Arming", instrument_id="eca1"))[1]
    assert on_dut["pos"] == 1 and "instrument_id" not in on_dut and "group" not in on_dut
    assert on_instrument["instrument_id"] == "eca1" and "pos" not in on_instrument
    assert decode_event("activity.progress", on_instrument).position == 0


def test_hello_says_who_is_calling_and_which_protocol():
    assert [p.wire for p in BY_WIRE["sys.hello"].params] == ["client", "protocol"]
    hello = inspect.signature(StationGateway.hello).parameters
    assert (hello["client"].default, hello["protocol"].default) == (CLIENT, PROTOCOL)


# ---- the app's models keep the protocol's fields --------------------------------------------------------------

def _protocol_types():
    for module in (common, dut, rf, registers, instruments, memory, advanced, station_tests):
        for name, value in vars(module).items():
            if isinstance(value, type) and value.__module__ == module.__name__ and (
                    dataclasses.is_dataclass(value) or issubclass(value, enum.Enum)):
                yield name, value


APP_MODULES = (app_station, facts, radio, app_registers)


@pytest.mark.parametrize("name, wire", list(_protocol_types()), ids=lambda v: v if isinstance(v, str) else "")
def test_every_app_model_of_a_protocol_type_has_its_fields_and_defaults(name, wire):
    """The app decodes station data into its own dataclasses (models/); one with a protocol type's name must have
    exactly its fields (and defaults, and enum values), or replies would be read wrong."""
    app = next((getattr(m, name) for m in APP_MODULES if isinstance(getattr(m, name, None), type)), None)
    if app is None:
        pytest.skip(f"the app has no model called {name}")
    if issubclass(wire, enum.Enum):
        assert {e.value for e in app} == {e.value for e in wire}
        return

    def shape(cls):
        return [(f.name, f.default if f.default is not dataclasses.MISSING else
                 f.default_factory() if f.default_factory is not dataclasses.MISSING else "required")
                for f in dataclasses.fields(cls)]
    assert shape(app) == shape(wire)
