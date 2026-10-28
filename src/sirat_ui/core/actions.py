"""Action and operation models (req §13), including legacy format migration."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Action:
    name: str
    operations: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True


def migrate_actions(raw: Any) -> "OrderedDict[str, Action]":
    """Accepts the current format and both legacy formats from req §13."""
    actions: "OrderedDict[str, Action]" = OrderedDict()
    if not isinstance(raw, dict):
        return actions
    for name, value in raw.items():
        if isinstance(value, dict) and "operations" in value:
            actions[name] = Action(name, list(value.get("operations") or []), bool(value.get("enabled", True)))
        elif isinstance(value, list):
            actions[name] = Action(name, list(value), True)
        elif isinstance(value, dict):
            actions[name] = Action(name, [{"register": reg, "value": val} for reg, val in value.items()], True)
    return actions


def actions_to_json(actions: "OrderedDict[str, Action]") -> Dict[str, Any]:
    return {a.name: {"operations": a.operations, "enabled": a.enabled} for a in actions.values()}


def op_kind(op: Dict[str, Any]) -> str:
    if op.get("type"):
        return str(op["type"])
    return "field_write" if "field" in op else "register_write"


def describe_op(op: Dict[str, Any]) -> str:
    kind = op_kind(op)
    if kind == "register_write":
        return f"{op['register']} = 0x{int(op['value']):08X}"
    if kind == "field_write":
        return f"{op['register']}.{op['field']} = 0x{int(op['value']):X}"
    if kind == "rf_switch":
        return f"RF switch → {op.get('path')} (DUT {op.get('dut_position', 1)})"
    if kind == "load_phy":
        return f"Load PHY {op.get('phy_name')}"
    if kind == "load_wifi_phy":
        c = op.get("config") or {}
        return f"Load WiFi PHY {c.get('phy_name')} ({c.get('mode')} {c.get('standard')} ch {c.get('channel')})"
    if kind == "signal_generator":
        return f"Siggen {op.get('sg_type')} {op.get('frequency_mhz')} MHz · {op.get('power_dbm')} dBm"
    if kind == "dut_reconnect":
        return op.get("description") or "Reconnect RPC"
    if kind == "custom_function":
        return f"Custom function {op.get('function_name')}"
    if kind == "dut_control_method":
        return f"{op.get('method_path')}()"
    if kind == "prs_route":
        return f"PRS {op.get('signal')} → {op.get('pin')} (ch {op.get('channel')})"
    if kind == "sequence":
        return f"Sequence {op.get('sequence_name')}"
    return kind.replace("_", " ")


def summarize_ops(ops: List[Dict[str, Any]]) -> str:
    count = f"{len(ops)} op" + ("" if len(ops) == 1 else "s")
    special = sorted({op_kind(o) for o in ops} - {"register_write", "field_write"})
    return count + (" · " + ", ".join(special) if special else "")


def main_kind(ops: List[Dict[str, Any]]) -> str:
    """The kind that best describes an action: its first non-register operation, else register_write."""
    kinds = [op_kind(op) for op in ops]
    special = [k for k in kinds if k not in ("register_write", "field_write")]
    return special[0] if special else (kinds[0] if kinds else "register_write")


CODE_KINDS = ("custom_function", "signal_generator", "gfsk_packet")
EDITABLE_KINDS = ("register_write", "field_write")
