"""DUT control API explorer (req 22): parameter parsing, error hints and the recorded action.

The tree itself comes from advanced.dut_control.describe; this module only turns what the user typed into
values and failures into advice.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Tuple

FORMAT_HINT = ("Formats: integers (100), hex (0xABCD), floats (3.14), scientific (2440e6), None, True/False. "
               "Leave a field empty to use its default.")

_HINTS = {
    "rpc_timeout": "The DUT didn't answer in time. Raise the timeout with dut.rta.lpw.SetRpcTimeout(seconds), "
                   "or re-initialise the radio with ReInit().",
    "rpc_transport": "The RPC link dropped. Reconnect with dut.rpc_io.Connect() (DUT menu → Reconnect RPC).",
    "rail_assert": "RAIL rejected the call. Check the parameters against the loaded PHY (frequency, channel, "
                   "power range).",
}


def parse_value(text: str, annotation: str = "") -> Any:
    """Req 22 "Parses parameter values", except that a str parameter keeps what was typed."""
    s = text.strip()
    if s.lower() == "none":
        return None
    if annotation == "str":
        return ast.literal_eval(s) if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"" else s
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lower().startswith(("0x", "-0x")):
        try:
            return int(s, 16)
        except ValueError:
            return s
    if re.fullmatch(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", s) and ("e" in s.lower() or "." in s):
        value = float(s)
        return int(value) if value.is_integer() and annotation != "float" else value
    try:
        return int(s)
    except ValueError:
        pass
    if s[:1] in "[({'\"":
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            pass
    return s


def default_text(default_repr: Optional[str]) -> str:
    """What to pre-fill: '1M' rather than "'1M'"."""
    if default_repr is None:
        return ""
    try:
        value = ast.literal_eval(default_repr)
    except (ValueError, SyntaxError):
        return default_repr
    return value if isinstance(value, str) else default_repr


def build_kwargs(params: List[Dict[str, Any]], texts: Dict[str, str]) -> Tuple[Dict[str, Any], List[str]]:
    """(kwargs, problems). Empty fields fall back to the default, and are a problem when there is none."""
    kwargs: Dict[str, Any] = {}
    problems: List[str] = []
    for p in params:
        text = texts.get(p["name"], "").strip()
        if not text:
            if p["required"]:
                problems.append(f"{p['name']} is required")
            continue
        if p.get("default_repr") is not None and text == default_text(p["default_repr"]):
            continue   # unchanged default: let the method use its own
        kwargs[p["name"]] = parse_value(text, p.get("annotation", ""))
    return kwargs, problems


def hint_for(cause: str) -> str:
    return _HINTS.get(cause, "")


def call_text(path: str, kwargs: Dict[str, Any]) -> str:
    return f"{path}(" + ", ".join(f"{k}={v!r}" for k, v in kwargs.items()) + ")"


def method_op(path: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Req 22 "Adding to Actions"."""
    return {"type": "dut_control_method", "method_path": path, "method_name": path.rsplit(".", 1)[-1],
            "params": dict(kwargs)}


def action_name(path: str) -> str:
    """The last two parts of the path: radio_SetPower."""
    return "_".join(path.split(".")[-2:])
