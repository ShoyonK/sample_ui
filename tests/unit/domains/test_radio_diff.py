"""Radio Calculator diff (req 21): parse a .cfg, pick peripherals, compare each field with the chip."""

from pathlib import Path

import pytest

from sirat_ui.core.radio_config import parse_config

SAMPLE = Path(__file__).resolve().parents[3] / "docs" / "samples" / "PHY_demo.cfg"


def run_diff(h, path=SAMPLE, uncheck=()):
    vm = h.shell.dumps
    h.ix.answer_open(str(path))
    vm.openRadioDiff()
    names = [r["name"] for r in h.shell.dumpPicker.peripherals.items]
    for name in uncheck:
        h.shell.dumpPicker.togglePeripheral(names.index(name))
    h.shell.dumpPicker.startPicked()
    h.scheduler.run_pending()
    return h.shell.comparison


def rows(vm):
    return {f'{r["peripheral"]}.{r["register"]}.{r["field"]}': r for r in vm.radioRows.items}


@pytest.mark.req("21.select")
def test_picker_shows_the_config_peripherals_with_field_counts_all_checked(harness):
    vm = harness.shell.dumps
    harness.ix.answer_open(str(SAMPLE))
    vm.openRadioDiff()
    assert harness.shell.dumpPicker.pickerOpen and harness.shell.dumpPicker.pickerTitle == "Select peripherals for comparison" and harness.shell.dumpPicker.pickerConfirm == "Compare"
    labels = [r["label"] for r in harness.shell.dumpPicker.peripherals.items]
    assert labels == ["MODEM (4 fields)", "SYNTH (2 fields)", "AGC (3 fields)", "FRC (1 field)", "USART0 (1 field)"]
    assert harness.shell.dumpPicker.checkedCount == 5


@pytest.mark.req("21.compare")
def test_each_field_is_a_match_mismatch_or_error(harness):
    vm = run_diff(harness)
    assert vm.resultKind == "radio" and vm.resultTitle == "Radio Calculator: PHY_demo.cfg"
    assert vm.resultSummary == "✓ 7 Matches | ⚠ 2 Mismatches | ❌ 2 Errors"
    r = rows(vm)
    assert r["MODEM.CTRL.OPMODE"]["status"] == "match"
    assert (r["MODEM.CTRL.DEMODSEL"]["status"], r["MODEM.CTRL.DEMODSEL"]["expected"],
            r["MODEM.CTRL.DEMODSEL"]["actual"]) == ("mismatch", "3", "0")
    assert (r["MODEM.CTRL.PREAMBLE"]["status"], r["MODEM.CTRL.PREAMBLE"]["actual"]) == ("error", "Field not found")
    assert r["USART0.RXDATA.RXDATA"]["actual"] == "Read-sensitive, not read"
    assert r["SYNTH.FREQ.FREQ"]["expected"] == "2440000 (0x253B40)"
    assert all(word in vm.resultHelp for word in ("Match", "Mismatch", "Error", "read-sensitive"))


def test_only_checked_peripherals_are_compared_and_each_register_is_read_once(harness):
    reads = []
    original = harness.services.registers.read
    harness.services.registers.read = lambda reg, **kw: (reads.append(reg.full_name), original(reg, **kw))[1]
    vm = run_diff(harness, uncheck=["SYNTH", "AGC", "FRC", "USART0"])
    assert {k.split(".")[0] for k in rows(vm)} == {"MODEM"}
    assert reads == ["MODEM.CTRL"]  # three fields, one read


def test_mismatches_follow_changes_on_the_chip(harness):
    harness.select("MODEM.CTRL")
    harness.shell.detail.write("0x302")  # DEMODSEL = 3
    harness.scheduler.run_pending()
    vm = run_diff(harness)
    assert rows(vm)["MODEM.CTRL.DEMODSEL"]["status"] == "match"
    assert vm.resultSummary.startswith("✓ 8 Matches | ⚠ 1 Mismatches")


@pytest.mark.req("21.sort")
def test_clicking_a_column_sorts_and_clicking_again_reverses(harness):
    vm = run_diff(harness)
    vm.sortBy("status")
    statuses = [r["status"] for r in vm.radioRows.items]
    assert statuses == ["mismatch"] * 2 + ["error"] * 2 + ["match"] * 7  # problems first
    assert vm.sortColumn == "status" and not vm.sortDescending
    vm.sortBy("status")
    assert [r["status"] for r in vm.radioRows.items][0] == "match" and vm.sortDescending
    vm.sortBy("field")
    assert [r["field"] for r in vm.radioRows.items][0] == "CHNO"


def test_save_report(harness, tmp_path):
    vm = run_diff(harness)
    report = tmp_path / "radio.csv"
    harness.ix.answer_save(str(report))
    vm.saveReport()
    lines = report.read_text(encoding="utf-8-sig").splitlines()
    assert lines[2] == "Peripheral,Register,Field,Expected,Actual,Status"
    assert "MODEM,CTRL,DEMODSEL,3,0,Mismatch" in lines and "MODEM,CTRL,PREAMBLE,1,Field not found,Error" in lines


def test_clear_removes_the_radio_result(harness):
    vm = run_diff(harness)
    vm.clearResult()
    assert vm.resultKind == "" and vm.radioRows.count == 0 and not vm.hasResult
    assert vm.resultHelp == ""  # the ? only shows for Radio Calculator results


def test_a_config_without_assignments_is_rejected(harness, tmp_path):
    empty = tmp_path / "empty.cfg"
    empty.write_text("# nothing here\nhello\n")
    harness.ix.answer_open(str(empty))
    harness.shell.dumps.openRadioDiff()
    assert harness.ix.alerts[-1].title == "No fields in the config"
    assert harness.shell.dumpPicker.pickerOpen is False


def test_needs_a_connection(qapp, tmp_path):
    from support import Harness
    h = Harness(tmp_path, connect=False)
    h.shell.dumps.openRadioDiff()
    assert ("error", "Connect to a DUT to compare with a Radio Calculator config") in h.ix.toasts


def test_parser_handles_comments_hex_and_bad_lines():
    config = parse_config("# header\nMODEM.CTRL.OPMODE = 2\nMODEM.FREQ.FREQ = 0x96000000  # 2440 MHz\n\n"
                          "not a line\nAGC.GAININDEX.INDEX = twelve\n", "x.cfg")
    assert [(e.path, e.expected) for e in config.entries] == [("MODEM.CTRL.OPMODE", 2),
                                                              ("MODEM.FREQ.FREQ", 0x96000000)]
    assert config.skipped == ["line 5: not a line", "line 6: AGC.GAININDEX.INDEX = twelve"]
    assert config.field_counts == {"MODEM": 2}


def test_skipped_lines_are_reported(harness, tmp_path):
    cfg = tmp_path / "p.cfg"
    cfg.write_text("MODEM.CTRL.OPMODE = 2\noops\n")
    harness.ix.answer_open(str(cfg))
    harness.shell.dumps.openRadioDiff()
    assert any("Skipped 1 line in p.cfg" in text for level, text in harness.ix.toasts if level == "warning")
