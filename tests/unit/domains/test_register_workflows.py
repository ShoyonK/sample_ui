"""Register read/write behaviour through the detail ViewModel (req 5, 7, 9)."""

import pytest

from sirat_ui.gateway.errors import ErrorCode
from sirat_ui.models.dialogs import ConfirmAnswer


@pytest.mark.req("5.auto-read")
def test_clicking_a_register_auto_reads_it_without_a_history_entry(harness):
    harness.select("BUFC.LPMODE")
    assert harness.shell.detail.valueText == "0x00000001"
    assert harness.services.history.entries == []


@pytest.mark.req("5.read")
def test_manual_read_shows_the_value_and_records_history(harness):
    harness.select("BUFC.LPMODE", by_user=False)
    harness.shell.detail.read()
    assert harness.shell.detail.valueText == "0x00000001"
    assert [(e.operation, e.target) for e in harness.services.history.entries] == [("READ", "BUFC.LPMODE")]


@pytest.mark.req("5.write")
def test_write_shows_the_read_back_value_and_highlights_changed_fields(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.detail.write("0x3")
    rows = {r["name"]: r for r in harness.shell.detail.fields.items}
    assert harness.shell.detail.valueText == "0x00000003"
    assert rows["LPENBYM33"]["changed"] is True
    assert rows["LPENBYM33"]["changedTip"] == "Value changed: was 0x0, now 0x1"
    assert rows["LPENBYSEQ"]["changed"] is False
    assert harness.services.history.entries[-1].operation == "WRITE"


def test_bad_input_shows_a_message_and_sends_nothing(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.detail.write("not a number")
    assert harness.ix.toasts[-1][0] == "error"
    assert harness.fake.calls_to("registers.write") == []


@pytest.mark.req("7.critical-confirm")
def test_critical_write_asks_first_and_writes_after_yes(harness):
    harness.select("CMU.CLKEN0")
    harness.ix.answer_next(True)
    harness.shell.detail.write("0xF0F")
    assert harness.ix.confirms[-1].title == "Confirm write to critical register"
    assert ("New value", "0x00000F0F") in harness.ix.confirms[-1].details
    assert harness.shell.detail.valueText == "0x00000F0F"


@pytest.mark.req("7.critical-cancel")
def test_cancelling_a_critical_write_changes_nothing(harness):
    harness.select("CMU.CLKEN0")
    harness.ix.answer_next(False)
    harness.shell.detail.toggleBit(3)
    assert harness.shell.detail.valueText == "0x00000F07"
    assert harness.fake.memory.values["CMU.CLKEN0"] == 0xF07


@pytest.mark.req("7.dont-show-again")
def test_dont_show_again_skips_future_confirmations(harness):
    harness.select("CMU.CLKEN0")
    harness.ix.answer_next(ConfirmAnswer(True, dont_show_again=True))
    harness.shell.detail.write("0xF0F")
    harness.shell.detail.write("0xF07")
    assert len(harness.ix.confirms) == 1
    assert harness.prefs.value.confirm_critical_writes is False


@pytest.mark.req("7.verify")
def test_failed_verification_warns_and_shows_the_read_back(harness):
    harness.select("BUFC.BUF0_CTRL")
    harness.shell.detail.write("0xFF")
    assert harness.ix.alerts[-1].title == "Write verification failed"
    assert "0x000000FF" in harness.ix.alerts[-1].message and "0x00000007" in harness.ix.alerts[-1].message
    assert harness.shell.detail.valueText == "0x00000007"


@pytest.mark.req("5.field-write")
def test_editing_a_field_writes_only_that_field(harness):
    harness.select("MODEM.CTRL")
    row = [r["name"] for r in harness.shell.detail.fields.items].index("OPMODE")
    harness.shell.detail.setFieldValue(row, "1")
    call = harness.fake.calls_to("registers.write_field")[-1]
    assert call.params == {"name": "MODEM.CTRL", "field": "OPMODE", "value": 1, "confirm": False}
    assert harness.services.history.entries[-1].target == "MODEM.CTRL.OPMODE"


@pytest.mark.req("7.range")
def test_out_of_range_field_values_are_rejected_before_sending(harness):
    harness.select("MODEM.CTRL")
    row = [r["name"] for r in harness.shell.detail.fields.items].index("OPMODE")
    harness.shell.detail.setFieldValue(row, "9")
    assert "out of range" in harness.ix.toasts[-1][1]
    assert harness.fake.calls_to("registers.write_field") == []


@pytest.mark.req("5.bit-toggle")
def test_clicking_a_bit_writes_the_register(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.detail.toggleBit(1)
    assert harness.shell.detail.bitValues[1] is True
    assert harness.shell.detail.valueText == "0x00000003"


@pytest.mark.req("5.format")
def test_display_format_applies_everywhere_and_persists(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.detail.setFormatIndex(1)
    assert harness.shell.detail.valueText == "1"
    assert harness.restart().prefs.value.value_format == "dec"


def test_write_only_registers_cannot_be_read(harness):
    harness.select("BUFC.BUF0_CMD")
    assert harness.shell.detail.canRead is False
    assert harness.shell.detail.canWrite is True


def test_read_errors_are_reported_not_raised(harness):
    harness.fake.fail_next("registers.read", ErrorCode.TIMEOUT)
    harness.select("BUFC.LPMODE")
    assert harness.ix.toasts[-1] == ("error", "Read BUFC.LPMODE: The station didn't answer in time.")
