import pytest

from sirat_ui.core import codegen, formula
from sirat_ui.core.actions import migrate_actions, op_kind, summarize_ops
from sirat_ui.core.requires import PositionFacts, check_requires


# ---- formulas (req 11) ---------------------------------------------------------------------

@pytest.mark.parametrize("expr, x, expected", [
    ("x / 1000", 2_440_000, 2440.0),
    ("(x ^ 0x8000) - 0x8000", 0xFFB4, -76.0),
    ("x * 40e6 / 2**19", 2**19, 40e6),
    ("pow(x, 0.5)", 16, 4.0),
    ("x * 3.3 / 4096", 4096, 3.3),
    ("max(x, 10) + pi - pi", 3, 10.0),
])
def test_formulas_evaluate(expr, x, expected):
    assert formula.evaluate(expr, x) == pytest.approx(expected)


@pytest.mark.parametrize("expr", ["__import__('os')", "open('x')", "x.real", "y + 1", "2 ** 10 ** 9", "", "x +",
                                  "sqrt(x)", "pow(2, 10000)"])
def test_unsafe_or_invalid_formulas_are_rejected_with_a_message(expr):
    assert formula.validate(expr)


@pytest.mark.req("11.format")
def test_format_result_uses_3_decimals_at_or_above_1_and_6_below():
    assert formula.format_result(2440.125, "MHz") == "2440.125 MHz"
    assert formula.format_result(-76.0, "dBm") == "-76.000 dBm"
    assert formula.format_result(0.0123456789, "V") == "0.012346 V"


# ---- requires (API doc: facts and requires) ------------------------------------------------

@pytest.mark.parametrize("method, facts, missing", [
    ("registers.read", PositionFacts(1), ["dut"]),
    ("registers.read", PositionFacts(1, dut_connected=True), []),
    ("registers.write", PositionFacts(1, dut_connected=True, activity="executing"), ["idle"]),
    ("radio.start_rx", PositionFacts(1, dut_connected=True), ["phy", "radio_rx"]),
    ("automation.seq.run", PositionFacts(1, dut_connected=True, fault="hardware"), ["no_fault"]),
    ("sys.status", None, []),
])
def test_requires_table(method, facts, missing):
    assert check_requires(method, facts) == missing


# ---- actions (req 13) and code generation (req 16) ------------------------------------------

def test_legacy_action_formats_are_migrated():
    actions = migrate_actions({
        "new": {"operations": [{"register": "A.B", "value": 1}], "enabled": False},
        "legacy_list": [{"register": "A.B", "value": 2}],
        "legacy_dict": {"A.B": 3, "C.D": 4},
    })
    assert actions["new"].enabled is False
    assert actions["legacy_list"].operations == [{"register": "A.B", "value": 2}]
    assert actions["legacy_dict"].operations == [{"register": "A.B", "value": 3}, {"register": "C.D", "value": 4}]


def test_op_kinds_and_summary():
    ops = [{"register": "A.B", "value": 1}, {"register": "A.B", "field": "F", "value": 1},
           {"type": "rf_switch", "path": "RX"}]
    assert [op_kind(o) for o in ops] == ["register_write", "field_write", "rf_switch"]
    assert summarize_ops(ops) == "3 ops · rf_switch"


def test_generated_code_is_valid_python_for_every_op_kind():
    actions = migrate_actions({"all": [
        {"register": "BUFC.LPMODE", "value": 3}, {"register": "MODEM.CTRL", "field": "OPMODE", "value": 2},
        {"type": "rf_switch", "path": "RX_PATH", "dut_position": 1}, {"type": "load_phy", "phy_name": "BLE_1M"},
        {"type": "signal_generator", "code": "siggen.trigger('RfOn')"}, {"type": "dut_reconnect"},
        {"type": "dut_control_method", "method_path": "common.ble.Start", "params": {"ch": 37}},
        {"type": "prs_route", "signal": "FRAMEDET", "pin": "PA0", "channel": 0},
        {"type": "custom_function", "function_name": "f"},
    ]})
    source = codegen.generate(actions.values())
    compile(source, "<generated>", "exec")
    assert "dut.rm.writeByName('BUFC.LPMODE', 0x00000003)" in source
