"""Register dumps (req 12): take a dump, compare two dumps, diff live values against a dump."""

import datetime as dt
import json

import pytest

from sirat_ui.core.dumps import compare, read_csv, to_csv, write_csv
from sirat_ui.models.dumps import RegisterDump


def dumps_dir(h):
    return h.home / ".sirat" / "dumps"


def take(h, peripherals, name="before", description=""):
    vm = h.shell.dumps
    vm.openPicker()
    h.shell.dumpPicker.selectNone()
    names = [r["name"] for r in h.shell.dumpPicker.peripherals.items]
    for p in peripherals:
        h.shell.dumpPicker.togglePeripheral(names.index(p))
    h.ix.answer_next({"name": name, "description": description})
    h.shell.dumpPicker.startPicked()
    h.scheduler.run_pending()


def file_names(h):
    return [r["name"] for r in h.shell.dumps.files.items]


def write_lpmode(h, value):
    h.select("BUFC.LPMODE")
    h.shell.detail.write(value)
    h.scheduler.run_pending()


@pytest.mark.req("12.take")
def test_take_a_dump_reads_the_checked_peripherals_and_saves_a_csv(harness):
    take(harness, ["BUFC", "SYNTH"], name="bring up")
    files = list(dumps_dir(harness).glob("bring up_*.csv"))
    assert len(files) == 1
    lines = files[0].read_text().splitlines()
    assert lines[0] == "Peripheral,Register,Address,Value"
    assert {line.split(",")[0] for line in lines[1:]} == {"BUFC", "SYNTH"}
    assert ("success", "Finished taking a dump \U0001F4A9") in harness.ix.toasts
    assert file_names(harness) == ["bring up"]
    assert harness.shell.dumps.selectedPath == str(files[0])


def test_picker_lists_peripherals_with_register_counts_and_select_all(harness):
    vm = harness.shell.dumps
    vm.openPicker()
    labels = [r["label"] for r in harness.shell.dumpPicker.peripherals.items]
    assert any(label.startswith("BUFC (") and label.endswith("registers)") for label in labels)
    harness.shell.dumpPicker.selectAll()
    assert harness.shell.dumpPicker.checkedCount == len(labels)
    harness.shell.dumpPicker.selectNone()
    assert harness.shell.dumpPicker.checkedCount == 0


def test_read_sensitive_and_write_only_registers_are_left_out(harness):
    sensitive = [r.full_name for p in harness.services.catalog.peripherals for r in p.registers
                 if r.read_sensitive or not r.access.readable]
    assert sensitive, "the fake chip should have some"
    harness.shell.dumps.openPicker()
    listed = {r["name"] for r in harness.shell.dumpPicker.peripherals.items}
    assert "USART0" not in listed  # nothing readable in it, so it isn't offered
    take(harness, sorted({n.split(".")[0] for n in sensitive} & listed))
    dump = read_csv(next(dumps_dir(harness).glob("*.csv")))
    assert not set(sensitive) & set(dump.values)


def test_cancelling_the_name_prompt_discards_the_dump(harness):
    vm = harness.shell.dumps
    vm.openPicker()
    harness.shell.dumpPicker.togglePeripheral(0)
    harness.ix.answer_next(None)
    harness.shell.dumpPicker.startPicked()
    harness.scheduler.run_pending()
    assert file_names(harness) == []
    assert ("info", "Dump discarded") in harness.ix.toasts


def test_taking_a_dump_needs_a_connection(qapp, tmp_path):
    from support import Harness
    h = Harness(tmp_path, connect=False)
    h.shell.dumps.openPicker()
    assert h.shell.dumpPicker.pickerOpen is False
    assert ("error", "Connect to a DUT to take a dump") in h.ix.toasts


@pytest.mark.req("12.diff_live")
def test_diff_vs_live_shows_changed_registers_with_field_changes(harness):
    write_lpmode(harness, "0x0")
    take(harness, ["BUFC"])
    write_lpmode(harness, "0x3")
    vm = harness.shell.dumps
    vm.select(0)
    vm.diffLive()
    harness.scheduler.run_pending()
    assert harness.shell.comparison.hasResult and harness.shell.comparison.resultTitle == "Live vs before" and harness.shell.comparison.afterLabel == "Live"
    row = next(r for r in harness.shell.comparison.rows.items if r["register"] == "BUFC.LPMODE")
    assert (row["before"], row["after"]) == ("0x00000000", "0x00000003")
    assert "→" in row["change"]
    assert harness.shell.comparison.resultSummary.startswith("1 register differs")


@pytest.mark.req("12.compare")
def test_compare_with_another_saved_dump_puts_the_older_one_first(harness):
    write_lpmode(harness, "0x0")
    take(harness, ["BUFC"], name="first")
    write_lpmode(harness, "0x3")
    harness.services.dumps._clock = lambda: dt.datetime.now().replace(microsecond=0) + dt.timedelta(seconds=5)
    take(harness, ["BUFC"], name="second")
    vm = harness.shell.dumps
    vm.select(file_names(harness).index("second"))
    vm.compareWith()  # cancelled: only to see the choices
    assert harness.shell.comparison.hasResult is False
    options = harness.ix.prompts[-1].fields[0].options
    assert len(options) == 1 and options[0].startswith("first · ")
    harness.ix.answer_next({"other": options[0]})
    vm.compareWith()
    assert harness.shell.comparison.resultTitle == "first vs second"
    assert [r["register"] for r in harness.shell.comparison.rows.items] == ["BUFC.LPMODE"]


def test_compare_files_uses_two_file_dialogs_and_saves_a_report(harness, tmp_path):
    a = write_csv(tmp_path, RegisterDump("a", dt.datetime(2026, 1, 1, 9), values={"MODEM.CTRL": 1, "CMU.X": 5}))
    b = write_csv(tmp_path, RegisterDump("b", dt.datetime(2026, 1, 1, 10), values={"MODEM.CTRL": 2, "AGC.Y": 1}))
    vm = harness.shell.dumps
    harness.ix.answer_open(str(b))
    harness.ix.answer_open(str(a))
    vm.compareFiles()
    assert harness.shell.comparison.resultTitle == "a vs b"  # older first, whatever order they were picked in
    assert harness.shell.comparison.resultSummary == "1 register differs · 1 compared"  # CMU and AGC aren't in both
    report = tmp_path / "report.csv"
    harness.ix.answer_save(str(report))
    harness.shell.comparison.saveReport()
    text = report.read_text(encoding="utf-8-sig")
    assert "Register,a (09:00:00),b (10:00:00),Change" in text and "MODEM.CTRL,0x00000001,0x00000002" in text


def test_compare_files_opens_in_the_dumps_folder(harness):
    harness.ix.answer_open("first.csv")
    harness.shell.dumps.compareFiles()
    folders = [folder for _, folder in harness.ix.open_requests]
    assert folders == [harness.services.dumps.directory] * 2


def test_a_diff_that_stops_part_way_says_why(harness):
    take(harness, ["BUFC"])
    vm = harness.shell.dumps
    vm.select(0)
    harness.fake.auto_resolve = False
    vm.diffLive()
    harness.fake.drop_dut(1, "RPC connection lost")
    harness.fake.auto_resolve = True
    harness.fake.release()
    harness.scheduler.run_pending()
    assert harness.ix.alerts[-1].title == "Comparison stopped"
    assert harness.shell.comparison.hasResult is False


def test_a_cancelled_diff_says_so(harness):
    take(harness, ["BUFC"])
    vm = harness.shell.dumps
    vm.select(0)
    harness.fake.auto_resolve = False
    vm.diffLive()
    harness.services.dumps.cancel()
    harness.fake.auto_resolve = True
    harness.fake.release()
    harness.scheduler.run_pending()
    assert harness.ix.toasts[-1] == ("info", "Comparison cancelled")
    assert harness.ix.alerts == []


def test_a_file_that_isnt_a_dump_shows_an_error(harness, tmp_path):
    bad = tmp_path / "notes.csv"
    bad.write_text("hello,world\n")
    harness.ix.answer_open(str(bad))
    harness.ix.answer_open(str(bad))
    harness.shell.dumps.compareFiles()
    assert harness.ix.alerts[-1].title == "Couldn't compare the dumps"
    assert harness.shell.comparison.hasResult is False


def test_delete_asks_first(harness):
    take(harness, ["BUFC"])
    vm = harness.shell.dumps
    vm.select(0)
    harness.ix.answer_next(True)
    vm.deleteSelected()
    assert file_names(harness) == [] and vm.selectedPath == ""


@pytest.mark.req("34.save")
def test_sessions_keep_the_dumps_taken_and_bring_back_missing_files(harness):
    take(harness, ["BUFC"], name="for session", description="before the fix")
    harness.ix.answer_next({"name": "with dump"})
    harness.shell.sessions.saveSession()
    saved = json.loads((harness.home / ".sirat" / "sessions" / "with dump.json").read_text())
    assert [(d["name"], d["description"]) for d in saved["dumps"]] == [("for session", "before the fix")]

    for path in dumps_dir(harness).glob("*.csv"):
        path.unlink()
    harness.services.sessions.load("with dump")
    assert file_names(harness) == ["for session"]


# ---- the file format and diff logic on their own ---------------------------------------------------

def test_csv_round_trip_keeps_name_time_values_and_addresses(tmp_path):
    dump = RegisterDump("rx: test", dt.datetime(2026, 10, 27, 14, 5, 9), values={"MODEM.CTRL": 0x12345678},
                        addresses={"MODEM.CTRL": 0x40086000})
    path = write_csv(tmp_path, dump)
    assert path.name == "rx_ test_20261027_140509.csv"
    assert to_csv(dump) == "Peripheral,Register,Address,Value\nMODEM,CTRL,0x40086000,0x12345678\n"
    back = read_csv(path)
    assert (back.name, back.timestamp, back.values, back.addresses) == (
        "rx_ test", dump.timestamp, dump.values, dump.addresses)


def test_compare_only_looks_at_peripherals_both_sides_have():
    result = compare({"A.R1": 1, "A.R2": 2, "B.R": 3}, {"A.R1": 1, "A.R2": 9, "C.R": 3}, lambda _: None,
                     title="t", before_label="x", after_label="y")
    assert [(r.register, r.before, r.after) for r in result.rows] == [("A.R2", 2, 9)]
    assert result.compared == 2 and result.only_in_one == 0
    assert result.rows[0].change == "bits 0x0000000B"
