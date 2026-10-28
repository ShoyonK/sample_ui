"""Peripheral tree (req 4, 6), favorites (req 8), notes (req 10), formulas (req 11)."""

import pytest


def names(harness):
    return [r["name"] for r in harness.shell.tree.model.items]


@pytest.mark.req("4.browse")
def test_tree_starts_collapsed_and_hides_secure_variants(harness):
    assert names(harness)[:4] == ["ACMP0", "AGC", "AMUXCP0", "BUFC"]
    assert "BUFC_NS" not in names(harness)
    assert all(r["kind"] == "peripheral" for r in harness.shell.tree.model.items)


@pytest.mark.req("4.expand")
def test_activating_a_peripheral_expands_it_and_again_collapses_it(harness):
    tree = harness.shell.tree
    row = names(harness).index("BUFC")
    tree.activate(row)
    assert "LPMODE" in names(harness)
    assert harness.shell.detail.mode == "peripheral"
    tree.activate(row)
    assert "LPMODE" not in names(harness)


@pytest.mark.req("6.search")
def test_search_filters_and_auto_selects_a_single_match(harness):
    harness.shell.tree.setSearchText("lpmode")
    harness.shell.tree.flushSearch()
    assert names(harness) == ["BUFC", "LPMODE"]
    assert harness.shell.detail.title == "BUFC.LPMODE"


@pytest.mark.req("4.read-all")
def test_read_all_registers_skips_read_sensitive_ones(harness):
    tree = harness.shell.tree
    tree.readAll(names(harness).index("BUFC"))
    assert harness.ix.toasts[-1] == ("info", "BUFC: 9 registers read, 0 failed")  # BUF0_CMD is write-only
    tree.readAll(names(harness).index("USART0"))
    assert harness.ix.toasts[-1] == ("info", "USART0: 0 registers read, 0 failed, 3 read-sensitive skipped")


@pytest.mark.req("4.read-all-progress")
def test_read_all_reports_progress_and_can_be_cancelled(harness):
    harness.fake.set_latency("registers.read", 40)  # one register per 40 ms, like a real station
    read_all = harness.shell.readAll
    harness.shell.tree.readAll(names(harness).index("BUFC"))
    assert read_all.isOpen and read_all.label == "Reading BUFC.IPVERSION…" and read_all.countText == "1 of 9"
    harness.scheduler.advance(40)
    assert read_all.countText == "2 of 9" and read_all.progress == pytest.approx(1 / 9)
    read_all.cancel()
    assert read_all.cancelling
    harness.scheduler.advance(40)  # the register in flight finishes, then it stops
    assert read_all.isOpen is False
    assert harness.ix.toasts[-1] == ("info", "BUFC: 2 registers read, 0 failed (cancelled)")
    assert harness.fake.calls_to("registers.read")[-1].params["name"] == "BUFC.EN"


def test_read_all_stops_when_the_dut_drops(harness):
    harness.fake.drop_after_reads = 3
    harness.shell.tree.readAll(names(harness).index("BUFC"))
    level, text = harness.ix.toasts[-1]
    assert level == "error" and "2 registers read, 1 failed" in text and "stopped" in text
    assert len(harness.fake.calls_to("registers.read")) == 3


def test_read_all_does_not_record_history_or_spam_messages(harness):
    harness.fake.fail_next("registers.read", __import__("sirat_ui.gateway.errors", fromlist=["ErrorCode"]).ErrorCode.TIMEOUT)
    harness.shell.tree.readAll(names(harness).index("BUFC"))
    assert harness.services.history.entries == []
    assert len(harness.ix.toasts) == 1 and "8 registers read, 1 failed" in harness.ix.toasts[0][1]


def test_tree_values_update_after_a_read(harness):
    harness.select("BUFC.LPMODE")
    row = next(r for r in harness.shell.tree.model.items if r["fullName"] == "BUFC.LPMODE")
    assert row["valueText"] == "0x00000001" and row["selected"] is True


def test_show_secure_preference_reveals_ns_variants(harness):
    harness.shell.settings.setShowSecure(True)
    assert "BUFC_NS" in names(harness)


@pytest.mark.req("8.favorites")
def test_favorites_toggle_hide_when_empty_and_persist(harness):
    favorites = harness.shell.favorites
    for name in list(harness.services.favorites.names):
        harness.services.favorites.remove(name)
    assert favorites.visible is False
    harness.select("GPIO.PA_DOUT")
    harness.shell.detail.toggleFavorite()
    assert favorites.visible is True and harness.shell.detail.isFavorite is True
    assert harness.restart().services.favorites.names == ["GPIO.PA_DOUT"]


def test_clicking_a_favorite_opens_and_reads_it(harness):
    favorites = harness.shell.favorites
    row = [r["fullName"] for r in favorites.model.items].index("SYNTH.FREQ")
    favorites.activate(row)
    assert harness.shell.detail.title == "SYNTH.FREQ" and harness.shell.detail.hasValue


@pytest.mark.req("10.notes")
def test_notes_save_on_edit_and_clear_when_emptied(harness):
    harness.select("BUFC.LPMODE")
    detail = harness.shell.detail
    row = [r["name"] for r in detail.fields.items].index("LPENBYSEQ")
    detail.setNote(row, "  checked on rev A0  ")
    assert detail.fields.items[row]["note"] == "checked on rev A0" and detail.fields.items[row]["hasNote"]
    assert harness.restart().services.annotations.note("BUFC.LPMODE.LPENBYSEQ") == "checked on rev A0"
    detail.setNote(row, "")
    assert detail.fields.items[row]["hasNote"] is False


@pytest.mark.req("11.formulas")
def test_formula_adds_a_calculated_column(harness):
    harness.select("GPIO.PA_DOUT")
    detail = harness.shell.detail
    assert detail.showCalculated is False
    detail.editFormula(0)
    editor = harness.shell.formulaEditor
    assert editor.isOpen and editor.fieldName == "GPIO.PA_DOUT.DOUT" and editor.hasExisting is False
    editor.setExpr("x * 2")
    editor.setUnit("mV")
    editor.save()
    assert editor.isOpen is False and detail.showCalculated is True
    assert detail.fields.items[0]["calcText"] == "0.000000 mV"


def test_invalid_formula_is_rejected_with_a_message(harness):
    harness.select("GPIO.PA_DOUT")
    harness.shell.detail.editFormula(0)
    editor = harness.shell.formulaEditor
    editor.setExpr("import os")
    editor.save()
    assert editor.isOpen is True and editor.testOk is False and editor.testText
    assert harness.shell.detail.showCalculated is False


@pytest.mark.req("11.test")
def test_formula_test_button_evaluates_with_x_100(harness):
    harness.select("GPIO.PA_DOUT")
    harness.shell.detail.editFormula(0)
    editor = harness.shell.formulaEditor
    editor.useExample(2)  # x * 3.3 / 4096, V
    assert (editor.expr, editor.unit) == ("x * 3.3 / 4096", "V")
    editor.test()
    assert editor.testOk and editor.testText == "x = 100  →  0.080566 V"
    editor.setExpr("x +")
    editor.test()
    assert editor.testOk is False


@pytest.mark.req("11.remove")
def test_remove_formula_asks_first(harness):
    harness.select("SYNTH.FREQ")
    harness.shell.detail.editFormula(0)
    editor = harness.shell.formulaEditor
    assert editor.hasExisting and editor.expr == "x / 1000"
    harness.ix.answer_next(False)
    editor.remove()
    assert harness.services.annotations.formula("SYNTH.FREQ.FREQ") is not None
    harness.ix.answer_next(True)
    editor.remove()
    assert harness.ix.confirms[-1].title == "Remove formula"
    assert harness.services.annotations.formula("SYNTH.FREQ.FREQ") is None and editor.isOpen is False


@pytest.mark.req("8.sorted")
def test_favorites_are_listed_alphabetically(harness):
    harness.select("AGC.EN")
    harness.shell.detail.toggleFavorite()
    shown = [r["fullName"] for r in harness.shell.favorites.model.items]
    assert shown == sorted(shown) and shown[0] == "AGC.EN"
    assert harness.services.favorites.names[-1] == "AGC.EN"  # the saved order is untouched
