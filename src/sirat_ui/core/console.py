"""Python console and custom functions (req 15, 20): command history and how results become output lines.

Output levels: input (the echoed command), stdout, result, error, hint, note.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

Line = Tuple[str, str]   # (level, text)

FUNCTION_PLACEHOLDER = """# Write Python code here. Available:
#   dut - the connected DUT (dut.dut_control, dut.rpc_io, dut.rm, dut.rta)
#   time, math, struct and the bench utilities
# Variables you assign stay available to later runs and to the console.
# A top-level `return` gives the function a result.
#
# dut.dut_control.lpw.ble.StartAdvertising(0, 37)
# print("BLE advertising started")"""

DEFAULT_FUNCTION_CODE = 'rssi = dut.rta.lpw.GetRSSI()\nprint(f"RSSI: {rssi} dBm")\nreturn rssi\n'


class CommandHistory:
    """Req 20 "History Navigation": ↑ older, ↓ newer, wrapping at both ends; back to the end after running."""

    def __init__(self) -> None:
        self.commands: List[str] = []
        self.index = -1

    def add(self, command: str) -> None:
        if command.strip() and (not self.commands or self.commands[-1] != command):
            self.commands.append(command)
        self.index = -1

    def previous(self) -> Optional[str]:
        if not self.commands:
            return None
        self.index = len(self.commands) - 1 if self.index == -1 else (self.index - 1) % len(self.commands)
        return self.commands[self.index]

    def next(self) -> Optional[str]:
        if not self.commands:
            return None
        self.index = 0 if self.index == -1 else (self.index + 1) % len(self.commands)
        return self.commands[self.index]


def echo(code: str) -> List[Line]:
    lines = code.rstrip("\n").split("\n")
    return [("input", (">>> " if i == 0 else "... ") + line) for i, line in enumerate(lines)]


def result_lines(stdout: str, stderr: str, result_text: Optional[str], error_text: Optional[str]) -> List[Line]:
    out: List[Line] = []
    if stdout:
        out.append(("stdout", stdout.rstrip("\n")))
    if stderr:
        out.append(("error", stderr.rstrip("\n")))
    if error_text:
        out.append(("error", error_text))
    elif result_text is not None:
        out.append(("result", result_text))
    return out


WELCOME: List[Line] = [
    ("note", "SiRAT Python console. The code runs on the station, next to the DUT."),
    ("note", "dut is the connected DUT. Type help() or press Help for what else is available."),
]


def help_lines(names: Sequence[Tuple[str, str, str]]) -> List[Line]:
    """Req 20 "Help Command": the objects in the namespace, examples and keys."""
    out: List[Line] = [("result", "Available objects")]
    width = max((len(n) for n, _, _ in names), default=4)
    for name, type_name, doc in names:
        out.append(("stdout", f"  {name.ljust(width)}  {type_name}" + (f" · {doc}" if doc else "")))
    out += [
        ("result", "Examples"),
        ("stdout", "  dut.dut_control.lpw.radio.SetChannel(5)\n"
                   "  hex(dut.rm.readByName('CMU.CLKEN0'))\n"
                   "  data = dut.rpc_io.ReadByteBlock(0x20000000, 16)"),
        ("result", "Keys"),
        ("stdout", "  Enter runs · Shift+Enter adds a line · ↑ / ↓ step through history"),
    ]
    return out
