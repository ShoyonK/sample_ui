"""Pure helpers behind the Advanced page: memory formatting, DUT control parameters, console history."""

from sirat_ui.core.console import CommandHistory, echo, result_lines
from sirat_ui.core.dut_control import build_kwargs, default_text, parse_value
from sirat_ui.core.memory import dump_text, parse_number, rows, write_problem


def test_parse_number_hex_decimal_and_rejects():
    assert (parse_number("0x2000_0000"), parse_number("256"), parse_number("-1"), parse_number("zz")) == \
        (0x20000000, 256, None, None)


def test_dump_text_matches_the_requirement_layout():
    data = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88])
    assert dump_text(0x20000000, data, "Bytes").splitlines()[1] == \
        "0x20000000: 12 34 56 78 9A BC DE F0  11 22 33 44 55 66 77 88  |.4Vx.....\"3DUfw.|"
    assert dump_text(0x20000000, data, "Words").splitlines()[1] == \
        "0x20000000: 0x3412 0x7856 0xBC9A 0xF0DE 0x2211 0x4433 0x6655 0x8877"
    assert dump_text(0x20000000, data, "DWords").splitlines()[1] == \
        "0x20000000: 0x78563412 0xF0DEBC9A 0x44332211 0x88776655"


def test_rows_mark_changes_against_the_previous_read():
    old, new = bytes(8), bytes([0, 0, 1, 0, 0, 0, 0, 0])
    cells = rows(0x100, new, "Bytes", (0x100, old))[0].cells
    assert [c for _, c in cells] == [False, False, True, False, False, False, False, False]


def test_write_problems():
    assert write_problem("0x20000000", "0x1FF", 1) == "0x1FF doesn't fit in 1 byte"
    assert "inside one 4-byte word" in write_problem("0x20000003", "1", 2)
    assert write_problem("0x20000002", "0xFFFF", 2) == ""


def test_parse_value_follows_req_22():
    assert [parse_value(s) for s in ("none", "true", "0xAB", "2440e6", "3.5", "12", "hello")] == \
        [None, True, 0xAB, 2440000000, 3.5, 12, "hello"]
    assert parse_value("123", "str") == "123" and parse_value("1.0", "float") == 1.0


def test_build_kwargs_uses_defaults_for_empty_or_unchanged_fields():
    params = [{"name": "power", "annotation": "int", "default_repr": "0", "required": False},
              {"name": "channel", "annotation": "int", "default_repr": None, "required": True}]
    assert build_kwargs(params, {"power": "0", "channel": ""}) == ({}, ["channel is required"])
    assert build_kwargs(params, {"power": "5", "channel": "37"}) == ({"power": 5, "channel": 37}, [])
    assert default_text("'1M'") == "1M"


def test_history_and_output_lines():
    h = CommandHistory()
    assert h.previous() is None
    h.add("a")
    h.add("b")
    assert (h.previous(), h.previous(), h.next()) == ("b", "a", "b")
    assert echo("if x:\n    y") == [("input", ">>> if x:"), ("input", "...     y")]
    assert result_lines("out\n", "", "3", None) == [("stdout", "out"), ("result", "3")]
