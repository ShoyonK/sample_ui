"""Actions (req §13): legacy format migration and summaries. What each kind of operation does is in core/ops.py."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List

from sirat_ui.core.ops import op_kind
from sirat_ui.models.actions import Action


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


def summarize_ops(ops: List[Dict[str, Any]]) -> str:
    count = f"{len(ops)} op" + ("" if len(ops) == 1 else "s")
    special = sorted({op_kind(o) for o in ops} - {"register_write", "field_write"})
    return count + (" · " + ", ".join(special) if special else "")


def main_kind(ops: List[Dict[str, Any]]) -> str:
    """The kind that best describes an action: its first non-register operation, else register_write."""
    kinds = [op_kind(op) for op in ops]
    special = [k for k in kinds if k not in ("register_write", "field_write")]
    return special[0] if special else (kinds[0] if kinds else "register_write")


