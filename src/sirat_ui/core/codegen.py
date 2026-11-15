"""Python code generation (req 16), following the template and per-operation snippets in the requirements.

A sequence action (req 14 "Add to Actions Panel") runs its enabled actions in order (core/wire_ops.py), so its
code is theirs, in order, with a comment for each one skipped. Req 16: generated code is self-contained.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Set

from sirat_ui.core.ops import code_lines, op_kind
from sirat_ui.models.actions import Action

Lookup = Callable[[str], Optional[Action]]   # action name -> the action, for expanding sequences

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


def _action_lines(action: Action, functions: Mapping[str, str], lookup: Optional[Lookup],
                  seen: Set[str]) -> List[str]:
    lines: List[str] = []
    for op in action.operations:
        if op_kind(op) == "sequence" and lookup is not None:
            lines.extend(_sequence_lines(op, functions, lookup, seen | {action.name}))
        else:
            lines.extend(code_lines(op, functions))
    return lines


def _sequence_lines(op: Dict[str, Any], functions: Mapping[str, str], lookup: Lookup, seen: Set[str]) -> List[str]:
    """The same actions a run of this sequence sends, skipped ones as comments."""
    lines = [f"# Sequence: {op.get('sequence_name', '')}"]
    for name in op.get("action_names") or []:
        inner = lookup(name)
        if inner is None:
            lines.append(f"# {name}: not found, skipped")
        elif not inner.enabled:
            lines.append(f"# {name}: disabled, skipped")
        elif name in seen:
            lines.append(f"# {name}: already part of this sequence, skipped")
        else:
            lines.append(f"# Action: {name}")
            lines.extend(_action_lines(inner, functions, lookup, seen))
    return lines


def generate(actions: Iterable[Action], custom_functions: Optional[Mapping[str, str]] = None,
             now: Optional[dt.datetime] = None, lookup: Optional[Lookup] = None) -> str:
    """Builds the req 16 script for a list of actions.

    Args:
        actions: The actions to include, in order.
        custom_functions: Custom function name -> code, so custom_function ops inline their code.
        now: The time written in the header; the current time when None (tests pass a fixed one).
        lookup: Finds an action by name, so a sequence action expands into its actions' code. Without it a
            sequence op becomes a one-line comment.

    Returns:
        The whole script as text.
    """
    functions = custom_functions or {}
    blocks = [[f"# Action: {action.name}"] + _action_lines(action, functions, lookup, set()) for action in actions]
    return _script(blocks, "Actions", now)


def generate_from_ops(ops: Iterable[Dict[str, Any]], title: str = "Operation history",
                      now: Optional[dt.datetime] = None) -> str:
    """Req 16: "generate Python code from action history"."""
    lines = [f"# {title}"]
    for op in ops:
        lines.extend(code_lines(op, {}))
    return _script([lines], "History", now)
