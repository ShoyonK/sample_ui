"""Actions (req §13): legacy format migration and summaries. What each kind of operation does is in core/ops.py."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List

from sirat_ui.core.ops import op_kind
from sirat_ui.models.actions import Action

_REGISTER_KINDS = ("register_write", "field_write")


def migrate_actions(raw: Any) -> OrderedDict[str, Action]:
    """Reads the actions file in the current format or either legacy format from req §13.

    Args:
        raw: The parsed JSON: {name: {"operations": [...], "enabled": bool}}, {name: [ops]} or
            {name: {register: value}}. Anything that isn't a dict gives no actions.

    Returns:
        The actions in file order, keyed by name.
    """
    actions: OrderedDict[str, Action] = OrderedDict()
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


def actions_to_json(actions: OrderedDict[str, Action]) -> Dict[str, Any]:
    """The actions in the current file format, ready for json.dumps."""
    return {a.name: {"operations": a.operations, "enabled": a.enabled} for a in actions.values()}


def summarize_ops(ops: List[Dict[str, Any]]) -> str:
    """A list line for an action: "3 ops", plus the non-register kinds it uses ("4 ops · load_phy, rf_switch")."""
    count = f"{len(ops)} op" + ("" if len(ops) == 1 else "s")
    special = sorted({op_kind(o) for o in ops} - set(_REGISTER_KINDS))
    return count + (" · " + ", ".join(special) if special else "")


def main_kind(ops: List[Dict[str, Any]]) -> str:
    """The kind that best describes an action: its first non-register operation, else register_write."""
    kinds = [op_kind(op) for op in ops]
    special = [k for k in kinds if k not in _REGISTER_KINDS]
    return special[0] if special else (kinds[0] if kinds else "register_write")


