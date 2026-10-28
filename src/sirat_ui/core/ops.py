"""Operation kinds (req 13, 16): everything the client knows about one kind of operation, in one place.

An operation is a dict saved in an action ({"type": "rf_switch", "path": ...}; register writes have no type).
Each kind says how it reads in lists, what Python it generates, what goes on the wire for automation.seq.run,
and whether it carries code or can be edited in the action editor. To add a kind, add one OpKind here; the
tests then ask for its schema (stores/schemas/operations.py) and its color (qml/theme/Theme.qml).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

Op = Dict[str, Any]
Functions = Mapping[str, str]          # custom function name -> code (~/.sirat_custom_functions.json)

DEFAULT_SIGGEN = "siggen1"   # until the Instruments page picks one, the station's first signal generator


class WireError(ValueError):
    """An op that can't be sent (e.g. a custom function whose code is missing)."""


@dataclass(frozen=True)
class OpKind:
    name: str
    describe: Callable[[Op], str]
    code: Callable[[Op, Functions], List[str]]
    wire_fields: Optional[Tuple[str, ...]] = None    # fields sent besides "type"; None: never sent as is
    to_wire: Optional[Callable[[Op, Functions], Op]] = None   # when the wire shape differs from the file
    carries_code: bool = False                       # shown with a code view in the action editor
    editable: bool = False                           # the action editor's register/field rows

    def wire(self, op: Op, functions: Functions) -> Op:
        if self.to_wire is not None:
            return self.to_wire(op, functions)
        if self.wire_fields is None:
            raise WireError(f"'{self.name}' operations can't be run on the station")
        return {"type": self.name, **{k: op[k] for k in self.wire_fields if k in op}}


KINDS: Dict[str, OpKind] = {}


def _register(kind: OpKind) -> None:
    KINDS[kind.name] = kind


def op_kind(op: Op) -> str:
    if op.get("type"):
        return str(op["type"])
    return "field_write" if "field" in op else "register_write"


def kind_of(op: Op) -> Optional[OpKind]:
    return KINDS.get(op_kind(op))


def describe_op(op: Op) -> str:
    kind = kind_of(op)
    return kind.describe(op) if kind else op_kind(op).replace("_", " ")


def code_lines(op: Op, functions: Functions) -> List[str]:
    kind = kind_of(op)
    return kind.code(op, functions) if kind else [f"# Unsupported operation: {op_kind(op)}"]


def to_wire(op: Op, functions: Functions) -> Op:
    kind = kind_of(op)
    if kind is None:
        raise WireError(f"'{op_kind(op)}' operations can't be run on the station")
    return kind.wire(op, functions)


def carries_code(kind: str) -> bool:
    return kind in KINDS and KINDS[kind].carries_code


def editable(kind: str) -> bool:
    return kind in KINDS and KINDS[kind].editable


# ---- register access ------------------------------------------------------------------------------------

_register(OpKind(
    "register_write",
    describe=lambda op: f"{op['register']} = 0x{int(op['value']):08X}",
    code=lambda op, _: [f"dut.rm.writeByName('{op['register']}', 0x{int(op['value']):08X})"],
    wire_fields=("register", "value"), editable=True))

_register(OpKind(
    "field_write",
    describe=lambda op: f"{op['register']}.{op['field']} = 0x{int(op['value']):X}",
    code=lambda op, _: [f"dut.rm.writeByName('{op['register']}.{op['field']}', {int(op['value'])})"],
    wire_fields=("register", "field", "value"), editable=True))

_register(OpKind(   # only produced from History; never saved in an action
    "register_read",
    describe=lambda op: f"Read {op['register']}",
    code=lambda op, _: [f"value = dut.rm.readByName('{op['register']}')"]))


# ---- radio and bench -------------------------------------------------------------------------------------

def _describe_rf(op: Op) -> str:
    where = f" (DUT {op['dut_position']})" if "dut_position" in op else ""   # the wire op uses the run's DUT
    return f"RF switch → {op.get('path')}{where}"


_register(OpKind(
    "rf_switch", describe=_describe_rf,
    code=lambda op, _: [f"SwitchUtils._connect_switch_path_for_role_name('{op.get('path')}', "
                        f"dut_position={op.get('dut_position', 1)})"],
    wire_fields=("path",)))   # the run's position is the DUT position

_register(OpKind(
    "load_phy",
    describe=lambda op: f"Load PHY {op.get('phy_name')}",
    code=lambda op, _: [f"# PHY: {op.get('phy_name', '')}",
                        f"dut.{op.get('method_path') or op.get('method_name') or 'load_phy'}(dut)"],
    wire_fields=("phy_name", "method_name")))


def _describe_wifi(op: Op) -> str:
    c = op.get("config") or {}
    return f"Load WiFi PHY {c.get('phy_name')} ({c.get('mode')} {c.get('standard')} ch {c.get('channel')})"


_register(OpKind(
    "load_wifi_phy", describe=_describe_wifi,
    code=lambda op, _: [f"dut.configurators.phy.load_wifi_phy(**{op.get('config', {})!r})"],
    wire_fields=("config",)))

_register(OpKind(
    "prs_route",
    describe=lambda op: f"PRS {op.get('signal')} → {op.get('pin')} (ch {op.get('channel')})",
    code=lambda op, _: [f"pti_prs.setup_prs({op.get('signal')!r}, {op.get('pin')!r}, {op.get('channel')})"],
    wire_fields=("signal", "pin", "channel")))


def _describe_siggen(op: Op) -> str:
    if "config" in op:  # the wire shape: Hz inside config
        c = op["config"]
        return f"Siggen {c.get('sg_type')} {float(c.get('frequency_hz', 0)) / 1e6:g} MHz · {c.get('power_dbm')} dBm"
    return f"Siggen {op.get('sg_type')} {op.get('frequency_mhz')} MHz · {op.get('power_dbm')} dBm"


def _siggen_wire(op: Op, _: Functions) -> Op:
    """Req 25's file format (MHz, flat) -> the wire's SignalGeneratorOp {instrument_id, config}."""
    return {"type": "signal_generator", "instrument_id": op.get("instrument_id") or DEFAULT_SIGGEN,
            "config": {"sg_type": op.get("sg_type", "PacketSrw"),
                       "input_config_name": op.get("input_config_name", ""),
                       "frequency_hz": float(op.get("frequency_mhz", 0)) * 1e6,
                       "power_dbm": float(op.get("power_dbm", 0)),
                       "overrides": dict(op.get("overrides") or {})}}


def _code_block(title: str) -> Callable[[Op, Functions], List[str]]:
    def lines(op: Op, _: Functions) -> List[str]:
        code = (op.get("code") or "").strip()
        return [title] + (code.splitlines() if code else ["pass"])
    return lines


_register(OpKind(
    "signal_generator", describe=_describe_siggen, code=_code_block("# Signal Generator Configuration"),
    to_wire=_siggen_wire, carries_code=True))

_register(OpKind(
    "gfsk_packet",
    describe=lambda op: "GFSK packet",
    code=_code_block("# GFSK Packet"), wire_fields=("code",), carries_code=True))


# ---- Python on the DUT -------------------------------------------------------------------------------------

def _function_code(op: Op, functions: Functions) -> List[str]:
    name = op.get("function_name", "")
    code = functions.get(name)
    return [f"# Custom function: {name}"] + (code.splitlines() if code else ["# (function code not found)"])


def _function_wire(op: Op, functions: Functions) -> Op:
    """The service can't see the functions file, so the code travels with the op."""
    name = str(op.get("function_name", ""))
    code = functions.get(name)
    if not code:
        raise WireError(f"Custom function '{name}' isn't in your custom functions")
    return {"type": "custom_function", "function_name": name, "code": code}


_register(OpKind(
    "custom_function",
    describe=lambda op: f"Custom function {op.get('function_name')}",
    code=_function_code, to_wire=_function_wire, carries_code=True))


def _method_code(op: Op, _: Functions) -> List[str]:
    path = str(op.get("method_path", ""))
    method = op.get("method_name") or path.rsplit(".", 1)[-1]
    base = path[: -len(method) - 1] if path.endswith("." + method) else path
    return [f"dut.dut_control.{base}.{method}(**{op.get('params', {})!r})"]


_register(OpKind(
    "dut_control_method",
    describe=lambda op: f"{op.get('method_path')}()",
    code=_method_code, wire_fields=("method_path", "method_name", "params")))

_register(OpKind(
    "dut_reconnect",
    describe=lambda op: op.get("description") or "Reconnect RPC",
    code=lambda op, _: ["dut.rpc_io.Connect()"], wire_fields=("description",)))


# ---- composition -------------------------------------------------------------------------------------------

_register(OpKind(   # expanded into its actions' ops by the client (core/wire_ops.py), never sent
    "sequence",
    describe=lambda op: f"Sequence {op.get('sequence_name')}",
    code=lambda op, _: [f"# Sequence {op.get('sequence_name')}: {', '.join(op.get('action_names', []))}"]))
