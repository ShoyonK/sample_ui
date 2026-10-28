"""Python code generation (req 16), following the template and per-operation snippets in the requirements."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sirat_ui.core.actions import Action, op_kind

_HEADER = '''#!/usr/bin/env python
"""
Generated code from SiRAT {source}
Generated: {timestamp}
"""

# Imports
from tests.common_test_imports import *
from tests.utils.instrument_utils.switch_utils import SwitchUtils


def main(dut):
    """Execute actions."""
'''

_FOOTER = '''

if __name__ == '__main__':
    # Get DUT instance
    # dut = ...  # User must configure
    # main(dut)
    pass
'''


def _op_lines(op: Dict[str, Any], custom_functions: Mapping[str, str]) -> List[str]:
    kind = op_kind(op)
    if kind == "register_write":
        return [f"dut.rm.writeByName('{op['register']}', 0x{int(op['value']):08X})"]
    if kind == "field_write":
        return [f"dut.rm.writeByName('{op['register']}.{op['field']}', {int(op['value'])})"]
    if kind == "register_read":  # only produced from history
        return [f"value = dut.rm.readByName('{op['register']}')"]
    if kind == "custom_function":
        name = op.get("function_name", "")
        code = custom_functions.get(name)
        return [f"# Custom function: {name}"] + (code.splitlines() if code else ["# (function code not found)"])
    if kind == "rf_switch":
        return [f"SwitchUtils._connect_switch_path_for_role_name('{op.get('path')}', "
                f"dut_position={op.get('dut_position', 1)})"]
    if kind in ("signal_generator", "gfsk_packet"):
        code = (op.get("code") or "").strip()
        title = "# Signal Generator Configuration" if kind == "signal_generator" else "# GFSK Packet"
        return [title] + (code.splitlines() if code else ["pass"])
    if kind == "load_phy":
        method_path = op.get("method_path") or op.get("method_name") or "load_phy"
        return [f"# PHY: {op.get('phy_name', '')}", f"dut.{method_path}(dut)"]
    if kind == "load_wifi_phy":
        return [f"dut.configurators.phy.load_wifi_phy(**{op.get('config', {})!r})"]
    if kind == "dut_control_method":
        path = str(op.get("method_path", ""))
        method = op.get("method_name") or path.rsplit(".", 1)[-1]
        base = path[: -len(method) - 1] if path.endswith("." + method) else path
        return [f"dut.dut_control.{base}.{method}(**{op.get('params', {})!r})"]
    if kind == "dut_reconnect":
        return ["dut.rpc_io.Connect()"]
    if kind == "prs_route":
        return [f"pti_prs.setup_prs({op.get('signal')!r}, {op.get('pin')!r}, {op.get('channel')})"]
    if kind == "sequence":
        return [f"# Sequence {op.get('sequence_name')}: {', '.join(op.get('action_names', []))}"]
    return [f"# Unsupported operation: {kind}"]


def _script(blocks: List[List[str]], source: str, now: Optional[dt.datetime]) -> str:
    body: List[str] = []
    for block in blocks:
        body.extend(block)
        body.append("")
    if not body:
        body = ["pass"]
    indented = "\n".join(("    " + line) if line else "" for line in body).rstrip()
    stamp = (now or dt.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return _HEADER.format(source=source, timestamp=stamp) + indented + "\n" + _FOOTER


def generate(actions: Iterable[Action], custom_functions: Optional[Mapping[str, str]] = None,
             now: Optional[dt.datetime] = None) -> str:
    functions = custom_functions or {}
    blocks = []
    for action in actions:
        lines = [f"# Action: {action.name}"]
        for op in action.operations:
            lines.extend(_op_lines(op, functions))
        blocks.append(lines)
    return _script(blocks, "Actions", now)


def generate_from_ops(ops: Iterable[Dict[str, Any]], title: str = "Operation history",
                      now: Optional[dt.datetime] = None) -> str:
    """Req 16: "generate Python code from action history"."""
    lines = [f"# {title}"]
    for op in ops:
        lines.extend(_op_lines(op, {}))
    return _script([lines], "History", now)
