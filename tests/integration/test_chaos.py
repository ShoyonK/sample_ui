"""Chaos phase 2 (docs/CHAOS_TESTING.md): one fault at one moment.

Each test checks that the user is told what happened, nothing is left looking busy, and the next step works.
"""

import json
from pathlib import Path

import pytest

from sirat_ui.gateway.errors import ErrorCode
from sirat_ui.models.station import ActivityFinished, ActivityProgress

SAMPLE_CFG = Path(__file__).resolve().parents[2] / "docs" / "samples" / "PHY_demo.cfg"


def drop_on_next_reads(h, n):
    """The DUT drops on the n-th register read from now."""
    h.fake.drop_after_reads = h.fake.fake_registers.reads + n


def log_texts(h):
    return [line.text for line in h.services.log.lines]


def with_dut_2(h):
    h.fake.connect_dut(2)
    h.scheduler.run_pending()
    return h


# ---- the DUT drops mid-operation ------------------------------------------------------------------

def test_dut_drop_mid_action_run(harness):
    actions = harness.shell.actions
    actions.select_name("ble_1m_rx_setup")
    actions.runCurrent()
    harness.scheduler.advance(500)
    harness.fake.drop_dut(1)
    harness.scheduler.run_pending()
    assert actions.console.items[-1]["text"] == "✗ ble_1m_rx_setup: DUT 1 disconnected"
    assert harness.ix.toasts[-1] == ("error", "Run ble_1m_rx_setup: The DUT connection dropped.")
    assert not harness.services.actions.running


def test_dut_drop_mid_dump_saves_nothing(harness):
    drop_on_next_reads(harness, 3)
    harness.shell.dumps.dumpPeripheral("BUFC")
    harness.shell.dumpPicker.startPicked()
    harness.scheduler.run_pending()
    alert = harness.ix.alerts[-1]
    assert alert.title == "Dump stopped" and "Nothing was saved" in alert.message
    assert not harness.ix.prompts                     # never asked to name a partial dump
    assert not harness.shell.dumpProgress.isOpen and not harness.services.dumps.running


def test_dut_drop_mid_read_all_says_it_stopped(harness):
    drop_on_next_reads(harness, 3)
    harness.services.read_all.start(harness.services.catalog.peripheral("BUFC"))
    harness.scheduler.run_pending()
    level, text = harness.ix.toasts[-1]
    assert level == "error" and text.startswith("BUFC: 2 registers read, 1 failed (stopped: Disconnected")
    assert not harness.shell.readAll.isOpen


def test_dut_drop_mid_radio_diff(harness):
    drop_on_next_reads(harness, 2)
    harness.ix.answer_open(str(SAMPLE_CFG))
    harness.shell.dumps.openRadioDiff()
    harness.shell.dumpPicker.startPicked()
    harness.scheduler.run_pending()
    assert harness.ix.alerts[-1].title == "Comparison stopped"
    assert harness.shell.comparison.resultKind == "" and not harness.shell.dumpProgress.isOpen


def test_dut_drop_mid_custom_function(harness):
    harness.services.functions.create("f1")
    functions = harness.shell.customFunctions
    functions.select(0)
    harness.fake.auto_resolve = False
    functions.run()
    harness.fake.drop_dut(1)
    harness.fake.auto_resolve = True
    harness.fake.release()
    assert not functions.running
    assert functions.output.items[-1]["text"] == "That needs a connected DUT first."


def test_dut_drop_mid_memory_read(harness):
    harness.fake.auto_resolve = False
    harness.shell.memory.read()
    harness.fake.drop_dut(1)
    harness.fake.auto_resolve = True
    harness.fake.release()
    assert harness.ix.toasts[-1] == ("error", "Memory read: That needs a connected DUT first.")


def test_dut_drop_mid_logger_recording(harness):
    harness.shell.navigate("watch")
    harness.shell.logger.toggleRecording()
    harness.scheduler.advance(2000)
    samples = harness.services.logger.sample_count
    harness.fake.drop_dut(1)
    harness.scheduler.advance(5000)
    assert not harness.shell.logger.recording and harness.services.logger.sample_count == samples
    assert harness.shell.recovery.visible                      # the recovery dialog explains the drop


# ---- switching DUT position mid-operation ---------------------------------------------------------

def test_switching_dut_stops_the_watch_list_and_the_logger(harness):
    with_dut_2(harness)
    harness.shell.navigate("watch")
    harness.shell.watch.toggleLive()
    harness.shell.logger.toggleRecording()
    harness.shell.state.setPosition(2)
    assert not harness.services.watch.live and not harness.services.logger.recording
    assert harness.ix.toasts[-1] == ("info", "Watch list paused and data logger stopped: you switched to DUT 2. "
                                             "Your data is kept.")
    assert not harness.fake.fake_registers.watches                            # unsubscribed from DUT 1


def test_switching_dut_stops_a_dump_instead_of_mixing_two_duts(harness):
    with_dut_2(harness)
    harness.fake.set_latency("registers.read", 50)
    harness.shell.dumps.dumpPeripheral("BUFC")
    harness.shell.dumpPicker.startPicked()
    harness.scheduler.advance(120)
    harness.shell.state.setPosition(2)
    harness.scheduler.run_pending()
    assert {c.position for c in harness.fake.calls_to("registers.read")[-3:]} == {1}
    assert harness.ix.alerts[-1].title == "Dump stopped"
    assert "you switched to DUT 2" in harness.ix.alerts[-1].message and not harness.ix.prompts


def test_switching_dut_stops_read_all(harness):
    with_dut_2(harness)
    harness.fake.set_latency("registers.read", 50)
    harness.services.read_all.start(harness.services.catalog.peripheral("BUFC"))
    harness.scheduler.advance(120)
    harness.shell.state.setPosition(2)
    harness.scheduler.run_pending()
    assert "(stopped: you switched to DUT 2)" in harness.ix.toasts[-1][1]
    assert 2 not in {c.position for c in harness.fake.calls_to("registers.read")}


def test_a_read_that_returns_after_switching_dut_is_not_shown_as_the_new_duts(harness):
    with_dut_2(harness)
    reg = harness.register("BUFC.LPMODE")
    harness.services.registers.clear_cache()
    harness.fake.auto_resolve = False
    harness.services.registers.read(reg, manual=False)
    harness.shell.state.setPosition(2)
    harness.fake.auto_resolve = True
    harness.fake.release()
    assert "BUFC.LPMODE" not in harness.services.registers.values


def test_a_sequence_keeps_running_on_its_own_dut_after_switching(harness):
    with_dut_2(harness)
    seqs = harness.shell.sequences
    seqs.run()
    harness.scheduler.advance(500)
    harness.shell.state.setPosition(2)
    assert seqs.running
    harness.scheduler.run_pending()
    assert seqs.statusText == "Finished"
    assert {c.position for c in harness.fake.calls_to("automation.seq.run")} == {1}


# ---- clicking Run twice ---------------------------------------------------------------------------

def test_double_clicking_run_on_a_sequence_starts_it_once(harness):
    seqs = harness.shell.sequences
    seqs.run()
    seqs.run()
    assert len(harness.fake.calls_to("automation.seq.run")) == 1 and seqs.running
    harness.scheduler.run_pending()
    assert seqs.statusText == "Finished" and not [t for t in harness.ix.toasts if t[0] == "error"]


def test_double_clicking_run_on_an_action_runs_it_once(harness):
    actions = harness.shell.actions
    actions.select_name("ble_1m_rx_setup")
    actions.runCurrent()
    actions.runCurrent()
    harness.scheduler.run_pending()
    assert len(harness.fake.calls_to("automation.seq.run")) == 1
    assert not [t for t in harness.ix.toasts if t[0] == "error"]
    actions.runCurrent()                                  # and it runs again once the first is done
    assert len(harness.fake.calls_to("automation.seq.run")) == 2


# ---- exports that can't be written ----------------------------------------------------------------

@pytest.fixture
def unwritable(tmp_path):
    folder = tmp_path / "taken.csv"
    folder.mkdir()                                        # a folder where the file should go: writing fails
    return str(folder)


def test_an_eca_capture_save_that_fails_says_so(harness, unwritable):
    eca = harness.shell.eca
    eca.capture()
    harness.scheduler.advance(2000)
    harness.ix.answer_save(unwritable)
    eca.saveCsv()
    level, text = harness.ix.toasts[-1]
    assert level == "error" and text.startswith("Couldn't save taken.csv")


@pytest.mark.parametrize("vm_name, slot", [("history", "saveSelected"), ("log", "saveLog"),
                                           ("settings", "exportSettings")])
def test_exports_that_fail_say_so(harness, unwritable, vm_name, slot):
    harness.services.registers.read(harness.register("BUFC.LPMODE"))   # something in History to save
    vm = getattr(harness.shell, vm_name)
    if vm_name == "history":
        vm.select(0, "single")
    harness.ix.answer_save(unwritable)
    getattr(vm, slot)()
    level, text = harness.ix.toasts[-1]
    assert level == "error" and text.startswith("Couldn't")


# ---- the station service ------------------------------------------------------------------------

def test_a_station_restart_ends_runs_and_reconnect_does_a_full_connect(harness):
    harness.shell.navigate("watch")
    harness.shell.watch.toggleLive()
    seqs = harness.shell.sequences
    seqs.run()
    harness.scheduler.advance(500)
    harness.fake.restart_station()
    harness.scheduler.run_pending()
    assert not seqs.running and seqs.message == "Station service restarted"
    assert not harness.services.watch.live and not harness.state.connected
    recovery = harness.shell.recovery
    assert recovery.visible and recovery.cause == "Station service restarted"
    connects = len(harness.fake.calls_to("dut.connect"))
    recovery.reconnect()          # the restart forgot the bench setup, so this falls back to a full connect
    harness.scheduler.run_pending()
    assert harness.state.connected and len(harness.fake.calls_to("dut.connect")) == connects + 1


def test_a_duplicated_finished_event_finishes_once(harness):
    harness.fake.duplicate_next(ActivityFinished)
    harness.shell.sequences.run()
    harness.scheduler.run_pending()
    assert harness.shell.sequences.statusText == "Finished"
    assert sum("Sequence ble_rx_bringup finished" in t for t in log_texts(harness)) == 1


def test_events_for_an_unknown_activity_are_ignored(harness):
    harness.fake.events.emit(ActivityProgress("nope", 1, 1, 2, "x"))
    harness.fake.events.emit(ActivityFinished("nope", 1, False))
    assert harness.ix.toasts == [] and not harness.shell.sequences.running


def test_a_drop_on_the_dut_you_are_not_viewing_opens_its_recovery(harness):
    with_dut_2(harness)
    harness.fake.drop_dut(2)
    harness.scheduler.run_pending()
    assert harness.state.connected                         # still fine on DUT 1
    assert harness.shell.recovery.visible and harness.shell.recovery.position == 2


@pytest.mark.xfail(strict=True, reason="open question 1 in docs/CHAOS_TESTING.md: no watchdog yet")
def test_a_lost_finished_event_does_not_leave_the_page_running(harness):
    harness.fake.swallow_next(ActivityFinished)
    harness.shell.sequences.run()
    harness.scheduler.run_pending()
    assert not harness.shell.sequences.running


# ---- closing the app ------------------------------------------------------------------------------

def test_closing_the_app_mid_run_does_not_fail(harness):
    """Open question 2: the run carries on on the station; closing doesn't abort it (yet)."""
    harness.shell.sequences.run()
    harness.scheduler.advance(500)
    harness.container.stop()
    harness.scheduler.run_pending()
    assert harness.fake.facts[1].activity == "idle" and not harness.fake.calls_to("activity.abort")
    assert json.loads((harness.home / ".sirat" / "autosave.json").read_text(encoding="utf-8"))
