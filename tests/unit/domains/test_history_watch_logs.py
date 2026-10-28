"""History (req 9), code generation (req 16), watch list (req 18) and log view (req 35)."""

import datetime as dt
import json

import pytest

from sirat_ui.core import codegen
from sirat_ui.domains.logs.viewmodel import format_line
from sirat_ui.models.actions import Action
from sirat_ui.models.station import LogLine
from sirat_ui.shared.dialogs import DialogsViewModel


def make_history(h):
    """READ BUFC.LPMODE, WRITE BUFC.LPMODE, WRITE MODEM.CTRL.OPMODE (newest first in the panel)."""
    h.select("BUFC.LPMODE")
    h.shell.detail.read()
    h.shell.detail.write("0x3")
    h.select("MODEM.CTRL")
    row = [r["name"] for r in h.shell.detail.fields.items].index("OPMODE")
    h.shell.detail.setFieldValue(row, "1")


# ---- History ----------------------------------------------------------------------------------

@pytest.mark.req("9.multi-select")
def test_history_click_ctrl_and_shift_selection(harness):
    make_history(harness)
    history = harness.shell.history
    history.select(0, "single")
    history.select(2, "toggle")
    assert [r["selected"] for r in history.model.items] == [True, False, True]
    history.select(1, "range")  # from the anchor (row 2) to row 1
    assert [r["selected"] for r in history.model.items] == [False, True, True]
    history.select(1, "single")
    assert history.selectedCount == 1


@pytest.mark.req("9.save-json")
def test_save_selected_writes_the_req_9_json_format(harness, tmp_path):
    make_history(harness)
    history = harness.shell.history
    history.select(0, "single")
    history.select(2, "range")
    target = tmp_path / "history.json"
    harness.ix.answer_save(str(target))
    history.saveSelected()
    saved = json.loads(target.read_text())
    assert saved == [
        {"register": "BUFC.LPMODE", "operation": "read", "value": 1},
        {"register": "BUFC.LPMODE", "operation": "write", "value": 3, "field": None},
        {"register": "MODEM.CTRL", "operation": "write", "value": 1, "field": "OPMODE"},
    ]


def test_save_selected_needs_a_selection_and_respects_cancel(harness, tmp_path):
    make_history(harness)
    harness.shell.history.saveSelected()
    assert "Select" in harness.ix.toasts[-1][1]
    harness.shell.history.select(0, "single")
    harness.ix.answer_save(None)  # cancelled
    harness.shell.history.saveSelected()
    assert not any("Saved" in text for _, text in harness.ix.toasts)


@pytest.mark.req("16.from-history")
def test_generate_code_from_history(harness):
    make_history(harness)
    harness.shell.history.generateCode()
    title, code = harness.ix.codes[-1]
    assert title == "Code from history"
    assert "value = dut.rm.readByName('BUFC.LPMODE')" in code
    assert "dut.rm.writeByName('BUFC.LPMODE', 0x00000003)" in code
    assert "dut.rm.writeByName('MODEM.CTRL.OPMODE', 1)" in code
    compile(code, "<history>", "exec")


# ---- Code generation (req 16 template) -------------------------------------------------------

@pytest.mark.req("16.template")
def test_generated_script_follows_the_req_16_template():
    actions = [Action("rx", [
        {"type": "rf_switch", "path": "RX_PATH", "dut_position": 2},
        {"type": "load_phy", "phy_name": "BLE_1M", "method_path": "load_ble_phy"},
        {"type": "dut_control_method", "method_path": "common.ble.StartAdvertising",
         "method_name": "StartAdvertising", "params": {"channel": 37}},
        {"type": "custom_function", "function_name": "init_ble"},
    ])]
    code = codegen.generate(actions, {"init_ble": "print('Started')"}, now=dt.datetime(2026, 10, 27, 14, 23, 45))
    assert "Generated code from SiRAT Actions\nGenerated: 2026-10-27 14:23:45" in code
    assert "from tests.common_test_imports import *" in code
    assert "def main(dut):\n    \"\"\"Execute actions.\"\"\"\n    # Action: rx" in code
    assert "SwitchUtils._connect_switch_path_for_role_name('RX_PATH', dut_position=2)" in code
    assert "dut.load_ble_phy(dut)" in code
    assert "dut.dut_control.common.ble.StartAdvertising(**{'channel': 37})" in code
    assert "# Custom function: init_ble\n    print('Started')" in code
    assert "if __name__ == '__main__':" in code
    compile(code, "<generated>", "exec")


def test_code_dialog_copies_and_saves(qapp, tmp_path):
    target = tmp_path / "out.py"
    dialogs = DialogsViewModel(chooser=lambda *_: str(target))
    dialogs.show_code_dialog("Generated code", "def main(dut):\n    pass\n")
    assert dialogs.code["title"] == "Generated code" and "<pre" in dialogs.code["html"]
    dialogs.saveCode()
    assert target.read_text() == "def main(dut):\n    pass\n"
    dialogs.closeCode()
    assert dialogs.code == {}


# ---- Watch list (req 18) ---------------------------------------------------------------------

def watch_names(h):
    return [r["name"] for r in h.shell.watch.model.items]


@pytest.mark.req("18.write")
def test_write_a_value_from_the_watch_list(harness):
    watch = harness.shell.watch
    harness.ix.answer_next({"value": "0x1"})
    watch.writeValue(watch_names(harness).index("MODEM.CTRL.OPMODE"))
    assert harness.fake.calls_to("registers.write_field")[-1].params["value"] == 1
    assert harness.ix.prompts[-1].title == "Write MODEM.CTRL.OPMODE"


def test_read_only_watch_fields_cannot_be_written(harness):
    harness.shell.watch.writeValue(watch_names(harness).index("AGC.RSSI.RSSI"))
    assert "read-only" in harness.ix.toasts[-1][1]
    assert harness.ix.prompts == []


@pytest.mark.req("18.multi-select")
def test_delete_selected_and_add_selected_to_logger(harness):
    watch = harness.shell.watch
    names = watch_names(harness)
    watch.select(names.index("AGC.EN.EN"), "single")
    watch.select(names.index("RAC.STATUS.STATE"), "toggle")
    assert watch.selectedCount == 2
    watch.addSelectedToLogger()
    tracked = [s.name for s in harness.services.logger.series]
    assert "AGC.EN.EN" in tracked and "RAC.STATUS.STATE" in tracked
    watch.removeSelected()
    assert "AGC.EN.EN" not in watch_names(harness) and "RAC.STATUS.STATE" not in watch_names(harness)
    assert watch.selectedCount == 0


def test_watch_rate_outside_0_1_to_60_is_rejected(harness):
    harness.shell.watch.setIntervalText("0.01")
    assert "between 0.1 and 60" in harness.ix.toasts[-1][1]
    assert harness.shell.watch.intervalText == "1.0"


# ---- Log view (req 35) -----------------------------------------------------------------------

def test_log_lines_use_the_req_35_display_format():
    line = LogLine(dt.datetime(2026, 10, 27, 14, 23, 45, 123000).timestamp(), "warning", "ui", "Field value out of range")
    assert format_line(line) == "[14:23:45.123] [WARNING] Field value out of range"


@pytest.mark.req("35.filter")
def test_log_level_checkboxes_filter_independently(harness):
    log = harness.shell.log
    harness.services.log.debug("probe-debug")
    harness.services.log.error("probe-error")
    texts = lambda: [r["text"] for r in log.model.items]  # noqa: E731
    assert any("[DEBUG] probe-debug" in t for t in texts())
    log.toggleLevel(0)  # Debug off
    assert not any("probe-debug" in t for t in texts()) and any("probe-error" in t for t in texts())
    log.toggleLevel(1)  # Info off too: errors still shown
    assert all("[INFO]" not in t for t in texts())
    assert log.levelStates == [False, False, True, True]


@pytest.mark.req("35.search")
def test_log_search_highlights_and_steps_through_matches(harness):
    log = harness.shell.log
    for i in range(3):
        harness.services.log.info(f"needle {i}")
    moved = []
    log.currentMatchMoved.connect(moved.append)
    log.setSearchText("NEEDLE")  # case-insensitive
    assert log.matchText == "3 of 3"
    assert sum(r["match"] for r in log.model.items) == 3
    log.nextMatch()
    assert log.matchText == "1 of 3" and len(moved) == 2
    log.previousMatch()
    assert log.matchText == "3 of 3"
    log.setSearchText("nothing like this")
    assert log.matchText == "no matches"


@pytest.mark.req("35.save")
def test_save_log_writes_every_line(harness, tmp_path):
    target = tmp_path / "sirat.log"
    harness.ix.answer_save(str(target))
    harness.shell.log.saveLog()
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines and all(line.startswith("[") and "] [" in line for line in lines)


def test_reads_and_writes_produce_debug_lines(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.detail.write("0x3")
    debug = [l.text for l in harness.services.log.lines if l.level == "debug"]
    assert "Reading register BUFC.LPMODE" in debug and "Writing BUFC.LPMODE = 0x3" in debug


def test_log_pop_out_flag(harness):
    harness.shell.log.setPoppedOut(True)
    assert harness.shell.log.poppedOut


def test_watch_density_is_remembered_across_restarts(harness):
    watch = harness.shell.watch
    assert watch.large is False
    watch.setLarge(True)
    assert watch.large and harness.prefs.value.watch_density == "large"
    assert harness.restart().shell.watch.large  # saved in ~/.sirat/preferences.json
