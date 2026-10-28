"""Saved operations -> the ops sent with automation.seq.run (docs/API_DESIGN.md, "automation").

The action files keep the original formats and any extra keys; the wire rejects unknown fields. So each op is
reduced to its wire model, tagged with `group` (the action it came from, echoed in activity.progress),
custom-function code is copied in from the user's functions file (the service can't see it), and `sequence` ops
are expanded into their actions' ops, because a sequence never goes on the wire.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Set

from sirat_ui.core.ops import op_kind, to_wire
from sirat_ui.models.actions import Action


def action_ops(action: Action, actions: Callable[[str], Optional[Action]],
               custom_functions: Mapping[str, str], _seen: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """One action's wire ops, each tagged group=<action name>. Nested sequence ops expand in place."""
    seen = (_seen or set()) | {action.name}
    out: List[Dict[str, Any]] = []
    for op in action.operations:
        if op_kind(op) == "sequence":
            for name in op.get("action_names") or []:
                inner = actions(name)
                if inner is not None and inner.enabled and name not in seen:
                    out.extend(action_ops(inner, actions, custom_functions, seen))
            continue
        out.append({**to_wire(op, custom_functions), "group": action.name})
    return out
