"""Python code generation (req 16), following the template and per-operation snippets in the requirements."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sirat_ui.core.ops import code_lines
from sirat_ui.models.actions import Action

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


def generate(actions: Iterable[Action], custom_functions: Optional[Mapping[str, str]] = None,
             now: Optional[dt.datetime] = None) -> str:
    functions = custom_functions or {}
    blocks = []
    for action in actions:
        lines = [f"# Action: {action.name}"]
        for op in action.operations:
            lines.extend(code_lines(op, functions))
        blocks.append(lines)
    return _script(blocks, "Actions", now)


def generate_from_ops(ops: Iterable[Dict[str, Any]], title: str = "Operation history",
                      now: Optional[dt.datetime] = None) -> str:
    """Req 16: "generate Python code from action history"."""
    lines = [f"# {title}"]
    for op in ops:
        lines.extend(code_lines(op, {}))
    return _script([lines], "History", now)
