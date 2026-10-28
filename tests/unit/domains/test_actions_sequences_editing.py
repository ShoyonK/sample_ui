"""Actions (req 13) and Sequences (req 14) editing features."""

import pytest

from sirat_ui.core.highlight import highlight_python


def action_names(h):
    return [r["name"] for r in h.shell.actions.model.items]


def select_action(h, name):
    h.shell.actions.select(action_names(h).index(name))


# ---- Actions ---------------------------------------------------------------------------------

@pytest.mark.req("13.view")
def test_view_shows_operations_with_highlighted_code(harness):
    select_action(harness, "siggen_2440_0dbm")
    harness.shell.actions.viewCurrent()
    editor = harness.shell.actionEditor
    assert editor.viewOpen and editor.viewTitle == "View action: siggen_2440_0dbm"
    assert "signal generator" in editor.viewHtml and "<span" in editor.viewHtml
    editor.closeView()
    assert editor.viewOpen is False


@pytest.mark.req("13.edit")
def test_edit_changes_register_values_and_lists_other_ops_as_info(harness):
    select_action(harness, "ble_1m_rx_setup")
    harness.shell.actions.editCurrent()
    editor = harness.shell.actionEditor
    rows = editor.editRows.items
    assert [r["editable"] for r in rows] == [False, False, True, True]
    assert rows[2]["valueText"] == "0x00000431" and rows[3]["description"] == "MODEM.CTRL.OPMODE"
    editor.setEditValue(3, "0x1")
    editor.saveEdit()
    assert editor.editOpen is False
    assert harness.services.actions.get("ble_1m_rx_setup").operations[3]["value"] == 1
    assert harness.restart().services.actions.get("ble_1m_rx_setup").operations[3]["value"] == 1


def test_edit_rejects_bad_and_out_of_range_values(harness):
    select_action(harness, "ble_1m_rx_setup")
    harness.shell.actions.editCurrent()
    editor = harness.shell.actionEditor
    editor.setEditValue(3, "zz")
    editor.saveEdit()
    assert editor.editOpen is True and harness.ix.toasts[-1][0] == "error"
    editor.setEditValue(3, "0x9")  # OPMODE is 2 bits
    editor.saveEdit()
    assert "out of range" in harness.ix.toasts[-1][1]
    assert harness.services.actions.get("ble_1m_rx_setup").operations[3]["value"] == 2


@pytest.mark.req("13.deselect-all")
def test_deselect_all_unchecks_every_action(harness):
    harness.shell.actions.deselectAll()
    assert not any(r["enabled"] for r in harness.shell.actions.model.items)


@pytest.mark.req("13.type-style")
def test_actions_carry_their_main_kind_for_colors_and_icons(harness):
    kinds = {r["name"]: r["kind"] for r in harness.shell.actions.model.items}
    assert kinds == {"lpmode_on": "register_write", "ble_1m_rx_setup": "rf_switch",
                     "siggen_2440_0dbm": "signal_generator", "reconnect_rpc": "dut_reconnect"}


@pytest.mark.req("14.add-from-actions")
def test_add_checked_actions_to_a_new_sequence(harness):
    harness.ix.answer_next({"sequence": "New sequence…", "name": "quick"})
    harness.shell.actions.addCheckedToSequence()
    assert harness.services.sequences.sequences["quick"] == ["lpmode_on", "ble_1m_rx_setup", "reconnect_rpc"]


def test_add_checked_actions_to_an_existing_sequence(harness):
    harness.services.actions.deselect_all()
    harness.services.actions.set_enabled("lpmode_on", True)
    harness.ix.answer_next({"sequence": "lp_mode_check", "name": ""})
    harness.shell.actions.addCheckedToSequence()
    assert harness.services.sequences.sequences["lp_mode_check"] == ["lpmode_on", "lpmode_on"]
    prompt = harness.ix.prompts[-1]
    assert prompt.fields[0].options[0] == "New sequence…" and "lp_mode_check" in prompt.fields[0].options


@pytest.mark.req("13.console")
def test_run_output_goes_to_the_actions_console(harness):
    select_action(harness, "lpmode_on")
    harness.shell.actions.runCurrent()
    harness.scheduler.run_pending()
    lines = [r["text"] for r in harness.shell.actions.console.items]
    assert lines[0].startswith("▶ lpmode_on") and lines[-1] == "✓ lpmode_on finished"
    harness.shell.actions.console.clear()
    assert harness.shell.actions.console.count == 0


@pytest.mark.req("3.reconnect-action")
def test_disconnect_dialog_can_add_reconnect_to_actions(harness):
    harness.fake.drop_dut(1)
    harness.shell.recovery.addReconnectToActions()
    assert harness.services.actions.get("reconnect_rpc_2").operations == [
        {"type": "dut_reconnect", "description": "Reconnect RPC"}]


# ---- Sequences -------------------------------------------------------------------------------

def step_titles(h):
    return [r["title"] for r in h.shell.sequences.steps.items]


@pytest.mark.req("14.new-empty")
def test_new_sequences_start_empty(harness):
    harness.ix.answer_next({"name": "empty_one"})
    harness.shell.sequences.newSequence()
    assert harness.shell.sequences.selectedName == "empty_one" and step_titles(harness) == []


@pytest.mark.req("14.edit-steps")
def test_add_remove_and_move_actions_in_a_sequence(harness):
    seqs = harness.shell.sequences
    harness.ix.answer_next({"action": "lpmode_on"})
    seqs.addAction()
    assert step_titles(harness)[-1] == "lpmode_on"
    seqs.selectStep(3)
    seqs.moveSelectedStep(-1)
    assert step_titles(harness) == ["reconnect_rpc", "ble_1m_rx_setup", "lpmode_on", "siggen_2440_0dbm"]
    assert seqs.selectedStep == 2
    seqs.removeSelectedStep()
    assert step_titles(harness) == ["reconnect_rpc", "ble_1m_rx_setup", "siggen_2440_0dbm"]


@pytest.mark.req("14.rename")
def test_rename_keeps_position_and_description(harness):
    harness.ix.answer_next({"name": "rx_bringup"})
    harness.shell.sequences.renameSequence()
    assert list(harness.services.sequences.sequences)[0] == "rx_bringup"
    assert harness.services.sequences.description("rx_bringup").startswith("Reconnect")


def test_rename_to_an_existing_name_is_refused(harness):
    harness.ix.answer_next({"name": "lp_mode_check"})
    harness.shell.sequences.renameSequence()
    assert "already exists" in harness.ix.toasts[-1][1]
    assert "ble_rx_bringup" in harness.services.sequences.sequences


@pytest.mark.req("14.to-actions")
def test_a_sequence_can_be_added_to_the_actions_panel(harness):
    harness.shell.sequences.addToActions()
    op = harness.services.actions.get("ble_rx_bringup").operations[0]
    assert op == {"type": "sequence", "sequence_name": "ble_rx_bringup",
                  "action_names": ["reconnect_rpc", "ble_1m_rx_setup", "siggen_2440_0dbm"]}


@pytest.mark.req("14.console")
def test_sequence_console_shows_skips_progress_and_summary(harness):
    harness.shell.sequences.run()
    harness.scheduler.run_pending()
    lines = [r["text"] for r in harness.shell.sequences.console.items]
    assert lines[0] == "▶ Sequence ble_rx_bringup"
    assert any("siggen_2440_0dbm: disabled, skipped" in line for line in lines)
    assert "  → ble_1m_rx_setup" in lines
    assert lines[-1].startswith("✓ ble_rx_bringup finished · 2 action(s) done, 1 skipped")


# ---- highlighter (req 13/16) -----------------------------------------------------------------

def test_highlighter_marks_keywords_strings_comments_functions_and_numbers():
    out = highlight_python("def f(x):\n    # note\n    return print('hi', 42)\n")
    assert "font-weight:bold" in out           # keyword
    assert "&#x27;hi&#x27;" in out             # string, escaped
    assert "# note" in out and "print" in out
    assert out.startswith("<pre")


def test_highlighter_survives_broken_code():
    assert "if (" in highlight_python("if (")
