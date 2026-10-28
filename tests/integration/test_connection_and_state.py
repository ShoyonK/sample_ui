"""Cross-tab behaviour through the real container: connection, disconnect recovery, global state."""

import pytest

from sirat_ui.gateway.errors import ErrorCode


@pytest.mark.req("3.connect")
def test_connecting_from_the_sheet_loads_the_tree_and_enables_reads(disconnected):
    h = disconnected
    assert h.shell.state.connectionText == "Disconnected"
    assert h.shell.tree.model.count == 0
    h.fake.auto_resolve = False
    h.shell.connection.openSheet()
    h.shell.connection.connect()
    assert h.shell.state.connectionText == "Connecting…" and h.shell.connection.busy is True
    h.fake.release()
    h.fake.auto_resolve = True
    h.fake.release()
    assert h.shell.state.connectionText == "Connected"
    assert h.shell.state.chipLabel == "EFR32XG29XFULL · revA0"
    assert h.shell.tree.model.count == 12
    assert any("Connected" in r["text"] for r in h.shell.connection.console.items)


def test_connect_failure_is_shown_and_leaves_the_button_usable(disconnected):
    disconnected.fake.fail_next("dut.connect", ErrorCode.HARDWARE_ERROR, "J-Link not found")
    disconnected.shell.connection.connect()
    assert disconnected.shell.connection.busy is False
    assert disconnected.ix.toasts[-1][0] == "error"


@pytest.mark.req("3.disconnect-recovery")
def test_dut_drop_opens_recovery_disables_writes_and_reconnect_restores(harness):
    harness.select("BUFC.LPMODE")
    assert harness.shell.detail.canWrite is True
    harness.fake.drop_dut(1, "power cycle", "heartbeat")
    recovery = harness.shell.recovery
    assert recovery.visible is True and recovery.cause == "power cycle"
    assert harness.shell.detail.canWrite is False
    assert harness.shell.state.connectionText == "Disconnected"
    recovery.reconnect()
    assert recovery.reconnected is True
    assert harness.shell.detail.canWrite is True
    recovery.loadLpwPhy()  # opens the Radio and PHY page, where the PHY is chosen
    assert recovery.visible is False and harness.shell.currentPage == "radio"
    harness.shell.lpwPhy.load()
    harness.scheduler.run_pending()
    assert harness.shell.state.phyText == "PHY · BLE_1M"
    assert recovery.wifiAvailable is False  # Lion, not Everest


def test_disconnect_during_a_read_is_detected(harness):
    harness.fake.drop_after_reads = 1
    harness.select("BUFC.LPMODE")
    assert harness.shell.recovery.visible is True
    assert harness.shell.recovery.detectedBy == "registers.read"


def test_only_one_recovery_dialog_at_a_time(harness):
    harness.fake.drop_dut(1, "first")
    harness.fake.drop_dut(1, "second")
    assert harness.shell.recovery.cause == "first"


def test_writes_are_blocked_while_a_sequence_runs(harness):
    harness.select("BUFC.LPMODE")
    harness.shell.sequences.run()
    assert harness.shell.detail.canWrite is False
    assert harness.shell.state.activityText == "Activity executing"
    harness.scheduler.run_pending()
    assert harness.shell.detail.canWrite is True


def test_dark_mode_persists_across_restarts(harness):
    harness.shell.state.toggleDarkMode()
    assert harness.shell.state.darkMode is True
    assert harness.restart().shell.state.darkMode is True


def test_navigation_only_accepts_known_pages(harness):
    harness.shell.navigate("watch")
    assert harness.shell.currentPage == "watch"
    harness.shell.navigate("nope")
    assert harness.shell.currentPage == "watch"


def test_demo_data_never_overwrites_existing_settings(harness):
    harness.services.favorites.toggle("GPIO.LOCK")
    names = list(harness.services.favorites.names)
    assert harness.restart().services.favorites.names == names
