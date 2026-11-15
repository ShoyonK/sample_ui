"""Which protocol method each StationGateway method calls (station_protocol.catalog is the contract).

WIRE_OF is the whole mapping. Everything else comes from the two sides themselves: the protocol method's wire
parameters, and the gateway method's signature in gateway/port.py (its parameter names and the app types they
take, and the app type its Call resolves with). The protocol lists a method's parameters in the order the
gateway method takes them, which is checked here when the module loads, so the two can't drift apart quietly.

ApiStationGateway builds requests from a Binding and decodes replies into its `result` type; FakeStationServer
turns requests back into gateway calls with it.
"""

from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from station_protocol.catalog import BY_WIRE
from station_protocol.method import Method
from sibench_ui.gateway.port import StationGateway

WIRE_OF: Dict[str, str] = {
    # sys
    "hello": "sys.hello", "status": "sys.status", "subscribe": "sys.subscribe", "recover": "sys.recover",
    # dut
    "connect_dut": "dut.connect", "reconnect_dut": "dut.reconnect", "disconnect_dut": "dut.disconnect",
    "probe": "dut.probe", "load_phy": "dut.load_phy", "dut_info": "dut.info", "set_rpc_timeout": "dut.set_rpc_timeout",
    # rf
    "rf_paths": "rf.paths", "rf_connect": "rf.connect", "rf_disconnect": "rf.disconnect",
    "prs_route": "rf.prs_route", "prs_signals": "rf.prs_signals",
    # registers
    "register_tree": "registers.tree", "read_register": "registers.read", "read_many": "registers.read_many",
    "write_register": "registers.write", "write_field": "registers.write_field", "watch": "registers.watch",
    "unwatch": "registers.unwatch",
    # activities, automation, tests
    "abort_activity": "activity.abort", "run_sequence": "automation.seq.run",
    "list_tests": "tests.list", "run_tests": "tests.run",
    # instruments
    "list_instruments": "instruments.list", "connect_instrument": "instruments.connect",
    "siggen_get": "instruments.siggen.get", "siggen_set": "instruments.siggen.set",
    "siggen_waveforms": "instruments.siggen.waveforms", "siggen_trigger": "instruments.siggen.trigger",
    "siggen_rf": "instruments.siggen.rf", "chamber_read": "instruments.chamber.read",
    "chamber_set_temp": "instruments.chamber.set_temp", "chamber_wait_stable": "instruments.chamber.wait_stable",
    "eca_sources": "instruments.eca.sources", "eca_capture": "instruments.eca.capture",
    "eca_result": "instruments.eca.result",
    # memory
    "memory_read": "memory.read", "memory_write": "memory.write",
    # advanced
    "console_open": "advanced.console.open", "console_exec": "advanced.console.exec",
    "console_names": "advanced.console.names", "console_close": "advanced.console.close",
    "custom_function": "advanced.custom_function", "dut_control_describe": "advanced.dut_control.describe",
    "dut_control_invoke": "advanced.dut_control.invoke",
}


@dataclass(frozen=True)
class Binding:
    attr: str                              # the StationGateway method: "read_register"
    method: Method                         # the protocol method it calls: registers.read
    args: Tuple[Tuple[str, Any], ...]      # the gateway method's parameters, in order: (name, app type)
    result: Any                            # the app type its Call resolves with (None for Empty)


def _bind(attr: str, wire: str) -> Binding:
    method = BY_WIRE[wire]
    fn = getattr(StationGateway, attr)
    hints = typing.get_type_hints(fn)
    names = [n for n in inspect.signature(fn).parameters if n != "self"]
    if len(names) != len(method.params):
        raise TypeError(f"{attr} takes {names}, but {wire} has {[p.wire for p in method.params]}")
    (result,) = typing.get_args(hints["return"])
    result = None if result is type(None) else result
    if (result is None) != (method.result is None):
        raise TypeError(f"{attr} and {wire} disagree on whether there is a result")
    return Binding(attr, method, tuple((n, hints[n]) for n in names), result)


BY_ATTR: Dict[str, Binding] = {attr: _bind(attr, wire) for attr, wire in WIRE_OF.items()}
BY_WIRE_NAME: Dict[str, Binding] = {b.method.wire: b for b in BY_ATTR.values()}
assert set(BY_WIRE_NAME) == set(BY_WIRE), "every protocol method is bound to a gateway method"
