"""Watch list (req 18), data logger (req 17), history (req 9), actions (req 13), sequences (req 14)."""

import pytest


def by_name(model):
    return {r["name"]: r for r in model.items}


@pytest.mark.req("18.watch")
def test_watch_list_updates_live_and_highlights_changes(harness):
    watch = harness.shell.watch
    watch.toggleLive()
    assert watch.live is True
    harness.scheduler.advance(1000)
    harness.scheduler.advance(1000)
    rows = by_name(watch.model)
    assert rows["SYNTH.FREQ.FREQ"]["calcText"].endswith("MHz")
    assert rows["MODEM.CTRL.OPMODE"]["enumName"] == "RX"
    assert any(r["changed"] for r in rows.values())


@pytest.mark.req("18.add")
def test_eye_button_adds_a_field_to_the_watch_list(harness):
    harness.select("GPIO.PA_DOUT")
    harness.shell.registerShortcuts.addToWatch(harness.shell.detail.fields.get(0)["fullName"])
    assert "GPIO.PA_DOUT.DOUT" in by_name(harness.shell.watch.model)
    assert "GPIO.PA_DOUT.DOUT" in harness.restart().services.watch.saved_names


def test_watch_stops_when_the_dut_drops(harness):
    harness.shell.watch.toggleLive()
    harness.fake.drop_dut(1)
    assert harness.shell.watch.live is False


@pytest.mark.req("17.logger")
def test_data_logger_records_calculated_samples(harness):
    logger = harness.shell.logger
    logger.toggleRecording()
    harness.scheduler.advance(2000)
    assert logger.recording is True and logger.sampleCount >= 4
    series = by_name(logger.series)
    assert 2439 < series["SYNTH.FREQ.FREQ"]["points"][-1] < 2441


def test_logger_export_writes_csv(harness):
    logger = harness.shell.logger
    logger.toggleRecording()
    harness.scheduler.advance(1000)
    logger.exportCsv()
    exported = list((harness.home / ".sirat" / "exports").glob("*.csv"))
    assert exported and "SYNTH.FREQ.FREQ" in exported[0].read_text()


@pytest.mark.req("9.history")
def test_history_filters_and_creates_actions_from_writes(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.detail.read()
    harness.shell.detail.write("0x3")
    history = harness.shell.history
    assert [r["operation"] for r in history.model.items] == ["WRITE", "READ"]
    history.toggleReads()
    assert [r["operation"] for r in history.model.items] == ["WRITE"]
    history.select(0, "single")
    harness.ix.answer_next({"name": "lp_both"})
    history.createAction()
    assert harness.services.actions.get("lp_both").operations == [{"register": "BUFC.LPMODE", "value": 3}]


@pytest.mark.req("13.run")
def test_run_checked_actions_executes_them_in_order(harness):
    actions = harness.shell.actions
    actions.runSelected()
    harness.scheduler.run_pending()
    ops = harness.fake.calls_to("automation.seq.run")[-1].params["ops"]
    # reduced to the wire model and tagged with the action it came from (core/wire_ops.py)
    assert ops[0] == {"type": "register_write", "register": "BUFC.LPMODE", "value": 3, "group": "lpmode_on"}
    assert harness.fake.memory.values["MODEM.CTRL"] & 0x3 == 2


@pytest.mark.req("13.reorder")
def test_actions_reorder_toggle_and_persist(harness):
    actions = harness.shell.actions
    actions.select(1)
    actions.moveCurrent(-1)
    actions.toggleEnabled(0)
    restarted = harness.restart().services.actions
    assert list(restarted.actions)[:2] == ["ble_1m_rx_setup", "lpmode_on"]
    assert restarted.actions["ble_1m_rx_setup"].enabled is False


@pytest.mark.req("16.codegen")
def test_generate_code_shows_and_copies_python(harness):
    harness.shell.actions.generateCode()
    title, code = harness.ix.codes[-1]
    assert title == "Generated code"
    compile(code, "<generated>", "exec")


@pytest.mark.req("14.sequence")
def test_sequence_run_reports_progress_then_finishes(harness):
    seqs = harness.shell.sequences
    assert seqs.selectedName == "ble_rx_bringup"
    assert seqs.statusText == "Ready · 2 to run, 1 skipped"
    seqs.run()
    harness.scheduler.advance(500)
    assert seqs.running is True and seqs.statusText == "Running · action 1 of 2"
    assert [r["state"] for r in seqs.steps.items] == ["running", "pending", "skipped"]
    harness.scheduler.run_pending()
    assert seqs.statusText == "Finished"
    assert [r["state"] for r in seqs.steps.items] == ["done", "done", "skipped"]
    assert seqs.message == "Finished · 2 action(s) done, 1 skipped"


@pytest.mark.req("14.abort")
def test_sequence_abort(harness):
    seqs = harness.shell.sequences
    seqs.run()
    harness.scheduler.advance(500)
    seqs.abort()
    harness.scheduler.run_pending()
    assert seqs.running is False and seqs.statusText == "Failed"
    assert "failed" in [r["state"] for r in seqs.steps.items]


def test_sequences_need_an_idle_connected_dut(disconnected):
    assert disconnected.shell.sequences.canRun is False
    assert disconnected.shell.actions.canRun is False


@pytest.mark.req("14.skip-disabled")
def test_sequences_send_only_enabled_actions(harness):
    harness.shell.sequences.run()
    ops = harness.fake.calls_to("automation.seq.run")[-1].params["ops"]
    assert "signal_generator" not in [o.get("type") for o in ops]
    assert len(ops) == 5  # reconnect (1) + ble_1m_rx_setup (4); siggen is disabled


@pytest.mark.req("14.missing-action")
def test_missing_actions_are_skipped_with_a_warning(harness):
    harness.services.actions.remove("reconnect_rpc")
    seqs = harness.shell.sequences
    assert [r["state"] for r in seqs.steps.items] == ["missing", "pending", "skipped"]
    seqs.run()
    assert any("'reconnect_rpc' not found" in line.text for line in harness.services.log.lines)
    harness.scheduler.run_pending()
    assert seqs.statusText == "Finished"


def test_a_sequence_with_nothing_enabled_does_not_start(harness):
    harness.services.actions.set_enabled("lpmode_on", False)
    seqs = harness.shell.sequences
    seqs.select([r["name"] for r in seqs.sequenceList.items].index("lp_mode_check"))
    seqs.run()
    assert harness.fake.calls_to("automation.seq.run") == []
    assert "No enabled actions" in harness.ix.toasts[-1][1]


@pytest.mark.req("9.field-write")
def test_history_shows_field_writes_with_the_full_register_value(harness):
    harness.select("MODEM.CTRL")
    row = [r["name"] for r in harness.shell.detail.fields.items].index("OPMODE")
    harness.shell.detail.setFieldValue(row, "1")
    entry = harness.shell.history.model.items[0]
    assert entry["kind"] == "field_write" and entry["target"] == "MODEM.CTRL.OPMODE"
    assert entry["valueText"] == "0x1  (register 0x00000001)"


@pytest.mark.req("18.format")
def test_watch_values_follow_the_display_format(harness):
    harness.shell.watch.toggleLive()
    harness.scheduler.advance(1000)
    harness.shell.detail.setFormatIndex(1)
    rows = {r["name"]: r for r in harness.shell.watch.model.items}
    assert rows["MODEM.CTRL.OPMODE"]["valueText"] == "2"
    harness.shell.detail.setFormatIndex(2)
    rows = {r["name"]: r for r in harness.shell.watch.model.items}
    assert rows["MODEM.CTRL.OPMODE"]["valueText"] == "0b10"
