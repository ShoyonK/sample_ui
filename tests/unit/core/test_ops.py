"""core/ops.py is the one place an operation kind is defined; these keep the other two places in step."""

import re
from pathlib import Path

from sirat_ui.core.ops import KINDS, WireError, code_lines, describe_op, to_wire

PACKAGE = Path(__file__).resolve().parents[3] / "src" / "sirat_ui"
SAVED_KINDS = set(KINDS) - {"register_read"}      # register_read only exists in History


def test_every_saved_kind_has_a_file_schema():
    schema = (PACKAGE / "stores" / "schemas" / "operations.py").read_text(encoding="utf-8")
    declared = set(re.findall(r'type: Literal\["(\w+)"\]', schema)) | {"register_write", "field_write"}
    assert declared == SAVED_KINDS


def test_every_kind_has_a_color_in_the_theme():
    theme = (PACKAGE / "qml" / "theme" / "Theme.qml").read_text(encoding="utf-8")
    colored = set(re.findall(r"(\w+): \"#", theme)) | set(re.findall(r"(\w+): \"(?:ok|info|warn|split)\"", theme))
    assert SAVED_KINDS - colored == set()


def test_each_kind_describes_codes_and_wires_itself():
    op = {"type": "custom_function", "function_name": "init"}
    assert describe_op(op) == "Custom function init"
    assert code_lines(op, {"init": "x = 1"}) == ["# Custom function: init", "x = 1"]
    assert to_wire(op, {"init": "x = 1"}) == {"type": "custom_function", "function_name": "init", "code": "x = 1"}
    assert to_wire({"register": "CMU.CTRL", "value": 1, "note": "kept in the file"}, {}) == \
        {"type": "register_write", "register": "CMU.CTRL", "value": 1}


def test_kinds_that_never_go_on_the_wire_say_so():
    for op in ({"type": "sequence", "sequence_name": "s"}, {"type": "made_up"}):
        try:
            to_wire(op, {})
        except WireError as exc:
            assert "can't be run on the station" in str(exc)
        else:
            raise AssertionError(op)
