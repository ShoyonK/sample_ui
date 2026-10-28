"""End-to-end user journeys through the real QML window (docs/FRONTEND_PLAN.md section 7.5)."""

import pytest

from pages import Dialogs, RegistersPage, Ui

PAGES = ["registers", "watch", "actions", "sequences", "dumps", "radio", "instruments", "advanced", "tests",
         "settings"]


def test_every_page_loads_without_qml_warnings(running, qtbot):
    ui = Ui(running.app, qtbot)
    for page in PAGES:
        running.h.shell.navigate(page)
        ui.settle(40)
        assert ui.find(f"page_{page}").property("item") is not None, page


@pytest.mark.req("3.connect")
def test_connect_from_the_sheet(running_disconnected, qtbot):
    ui = Ui(running_disconnected.app, qtbot)
    assert ui.text("connectionPill") == "Disconnected"
    ui.click("connectionButton")
    ui.wait_for(lambda: ui.visible("connectButton"))
    ui.click("connectButton")
    ui.wait_for(lambda: ui.find("connectionPill").property("text") == "Connected")
    assert "EFR32XG29XFULL" in ui.text("chipLabel")
    ui.click("connectSheetCloseButton")
    ui.wait_for(lambda: ui.exists("treeRow_BUFC"))


@pytest.mark.req("5.read")
def test_search_open_and_read_a_register(running, qtbot):
    page = RegistersPage(running.app, qtbot)
    page.search("lpmode")
    page.wait_for(lambda: page.text("detailTitle") == "BUFC.LPMODE")
    page.click("readButton")
    assert page.value_text() == "0x00000001"
    assert running.h.shell.history.model.count == 1


@pytest.mark.req("5.write")
def test_type_a_value_and_write_it(running, qtbot):
    page = RegistersPage(running.app, qtbot)
    page.open_register("BUFC.LPMODE")
    page.write("0x3")
    assert page.value_text() == "0x00000003"
    assert running.h.fake.memory.values["BUFC.LPMODE"] == 3


@pytest.mark.req("7.critical-cancel")
def test_cancelled_bit_toggle_on_a_critical_register_sends_nothing(running, qtbot):
    page, dialogs = RegistersPage(running.app, qtbot), Dialogs(running.app, qtbot)
    page.open_register("CMU.CLKEN0")
    page.toggle_bit(3)
    page.wait_for(dialogs.confirm_open)
    dialogs.cancel_confirm()
    page.wait_for(lambda: not dialogs.confirm_open())
    assert running.h.fake.memory.values["CMU.CLKEN0"] == 0xF07
    assert page.value_text() == "0x00000F07"


@pytest.mark.req("7.critical-confirm")
def test_confirmed_critical_write_goes_through(running, qtbot):
    page, dialogs = RegistersPage(running.app, qtbot), Dialogs(running.app, qtbot)
    page.open_register("CMU.CLKEN0")
    page.write("0xF0F")
    page.wait_for(dialogs.confirm_open)
    dialogs.accept_confirm()
    page.wait_for(lambda: page.value_text() == "0x00000F0F")


@pytest.mark.req("7.verify")
def test_verification_failure_alert(running, qtbot):
    page, dialogs = RegistersPage(running.app, qtbot), Dialogs(running.app, qtbot)
    page.open_register("BUFC.BUF0_CTRL")
    page.write("0xFF")
    page.wait_for(dialogs.alert_open)
    page.click("alertOkButton")
    page.wait_for(lambda: not dialogs.alert_open())
    assert page.value_text() == "0x00000007"


@pytest.mark.req("5.field-write")
def test_double_click_a_field_value_and_press_enter(running, qtbot):
    page = RegistersPage(running.app, qtbot)
    page.open_register("MODEM.CTRL")
    page.click("fieldRow_OPMODE")
    value_cell = page.find("fieldValueEditor_OPMODE").parentItem()
    from PyQt5.QtCore import QPointF, Qt
    from PyQt5.QtTest import QTest
    center = value_cell.mapToScene(QPointF(value_cell.width() / 2, value_cell.height() / 2)).toPoint()
    QTest.mouseDClick(running.window, Qt.LeftButton, Qt.NoModifier, center)
    page.settle()
    page.type_text("fieldValueEditor_OPMODE", "1")
    page.wait_for(lambda: running.h.fake.memory.values["MODEM.CTRL"] & 0x3 == 1)


@pytest.mark.req("8.favorites")
def test_star_a_register_and_open_it_from_favorites(running, qtbot):
    page = RegistersPage(running.app, qtbot)
    page.open_register("GPIO.PA_DOUT")
    page.click("favoriteButton")
    page.wait_for(lambda: page.exists("favorite_GPIO.PA_DOUT"))
    page.open_register("BUFC.LPMODE")
    page.click("favorite_GPIO.PA_DOUT")
    assert page.text("detailTitle") == "GPIO.PA_DOUT"


@pytest.mark.req("3.disconnect-recovery")
def test_recover_after_a_dut_power_cycle(running, qtbot):
    page, dialogs = RegistersPage(running.app, qtbot), Dialogs(running.app, qtbot)
    page.open_register("BUFC.LPMODE")
    running.h.fake.drop_dut(1, "power cycle")
    page.wait_for(dialogs.recovery_open)
    assert not page.enabled("loadLpwPhyButton")
    page.click("reconnectButton")
    page.wait_for(lambda: page.enabled("loadLpwPhyButton"))
    assert page.text("recoveryStatus").startswith("Connected")
    page.click("recoveryCloseButton")
    page.wait_for(lambda: not dialogs.recovery_open())
    page.click("readButton")
    assert page.value_text().startswith("0x")


@pytest.mark.req("18.watch")
def test_start_the_watch_list(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("watchLiveButton"))
    ui.click("watchLiveButton")
    running.h.scheduler.advance(2000)
    ui.settle()
    assert ui.text("watchLiveButton") == "Pause"
    assert ui.exists("watchRow_SYNTH.FREQ.FREQ")


@pytest.mark.req("14.abort")
def test_run_and_abort_a_sequence(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("sequences")
    ui.wait_for(lambda: ui.exists("runSequenceButton"))
    ui.click("runSequenceButton")
    running.h.scheduler.advance(500)
    ui.settle()
    assert ui.text("runSequenceButton") == "Abort"
    ui.click("runSequenceButton")
    running.h.scheduler.run_pending()
    ui.settle()
    assert ui.text("runSequenceButton") == "Run"
    assert running.h.shell.sequences.statusText == "Failed"


def test_dark_mode_button(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.click("themeButton")
    assert running.h.shell.state.darkMode is True
    ui.navigate("settings")
    ui.wait_for(lambda: ui.exists("darkModeBox"))
    assert ui.find("darkModeBox").property("checked") is True


@pytest.mark.req("17.zoom")
def test_drag_on_a_logger_plot_zooms_every_plot(running, qtbot):
    from PyQt5.QtCore import QPointF, Qt
    from PyQt5.QtTest import QTest

    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("loggerRecordButton"))
    ui.click("loggerRecordButton")
    running.h.scheduler.advance(10_000)
    ui.wait_for(lambda: ui.exists("plot_SYNTH.FREQ.FREQ"))
    plot = ui.find("plot_SYNTH.FREQ.FREQ")
    area = [c for c in plot.childItems() if c.objectName() == "plotZoomArea"][0]
    y = area.height() / 2
    start = area.mapToScene(QPointF(area.width() * 0.2, y)).toPoint()
    end = area.mapToScene(QPointF(area.width() * 0.7, y)).toPoint()
    QTest.mousePress(running.window, Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(running.window, end)
    QTest.mouseRelease(running.window, Qt.LeftButton, Qt.NoModifier, end)
    ui.settle()
    vm = running.h.shell.logger
    assert 0 <= vm.zoomStart < vm.zoomEnd
    assert ui.find("plot_AGC.RSSI.RSSI").property("xMin") == vm.zoomStart
    ui.click("loggerResetZoomButton")
    assert vm.zoomStart == -1


@pytest.mark.req("13.view")
def test_view_and_edit_an_action_in_the_real_dialogs(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("actions")
    ui.wait_for(lambda: ui.exists("actionRow_ble_1m_rx_setup"))
    ui.click("actionRow_ble_1m_rx_setup")
    ui.click("actionsViewButton")
    ui.wait_for(lambda: ui.visible("actionViewDialog"))
    assert "rf switch" in ui.find("actionViewText").property("text")
    ui.click("actionViewCloseButton")
    ui.wait_for(lambda: not ui.visible("actionViewDialog"))

    ui.click("actionsEditButton")
    ui.wait_for(lambda: ui.visible("actionEditDialog"))
    ui.wait_for(lambda: ui.exists("editValue_3"))
    ui.type_text("editValue_3", "1", enter=False)
    ui.click("actionEditSaveButton")
    ui.wait_for(lambda: not ui.visible("actionEditDialog"))
    assert running.h.services.actions.get("ble_1m_rx_setup").operations[3]["value"] == 1


@pytest.mark.req("14.edit-steps")
def test_reorder_a_sequence_with_the_buttons(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("sequences")
    ui.wait_for(lambda: ui.exists("step_siggen_2440_0dbm"))
    ui.click("step_siggen_2440_0dbm")
    ui.click("stepUpButton")
    order = running.h.services.sequences.sequences["ble_rx_bringup"]
    assert order == ["reconnect_rpc", "siggen_2440_0dbm", "ble_1m_rx_setup"]
    ui.click("removeStepButton")
    assert running.h.services.sequences.sequences["ble_rx_bringup"] == ["reconnect_rpc", "ble_1m_rx_setup"]


@pytest.mark.req("14.add-from-actions")
def test_add_checked_actions_to_an_existing_sequence_through_the_dropdown(running, qtbot):
    from PyQt5.QtCore import Qt
    ui = Ui(running.app, qtbot)
    ui.navigate("actions")
    ui.wait_for(lambda: ui.exists("actionAddToSequenceButton"))
    ui.click("actionAddToSequenceButton")
    ui.wait_for(lambda: ui.visible("promptDialog"))
    combo = ui.find("promptChoice_sequence")
    combo.setProperty("currentIndex", 2)  # "lp_mode_check"
    combo.activated.emit(2)
    ui.click("promptSubmitButton")
    ui.wait_for(lambda: len(running.h.services.sequences.sequences["lp_mode_check"]) == 4)


@pytest.mark.req("17.rate")
def test_sample_rate_applies_when_leaving_the_field_and_rejects_bad_values(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("loggerRateField"))
    ui.click("loggerRateField")
    for ch in "0.25":
        ui._key(0, ch)  # the click selected the old value, so typing replaces it
    ui.click("watchIntervalField")  # leave the field without pressing Enter
    assert running.h.shell.logger.rateText == "0.25"

    ui.click("loggerRateField")
    for ch in "9999":
        ui._key(0, ch)
    ui.click("watchIntervalField")
    ui.wait_for(lambda: ui.text("loggerRateField") == "0.25")  # rejected value snaps back
    assert running.h.shell.logger.rateText == "0.25"


@pytest.mark.req("18.rate")
def test_watch_refresh_rate_applies_when_leaving_the_field(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("watchIntervalField"))
    ui.click("watchIntervalField")
    for ch in "2.5":
        ui._key(0, ch)
    ui.click("loggerRateField")
    assert running.h.shell.watch.intervalText == "2.5"


@pytest.mark.req("11.test")
def test_formula_dialog_test_and_save(running, qtbot):
    page = RegistersPage(running.app, qtbot)
    page.open_register("GPIO.PA_DOUT")
    page.click("formulaButton_DOUT")
    page.wait_for(lambda: page.visible("formulaDialog"))
    page.click("formulaExample_2")
    page.click("formulaTestButton")
    page.wait_for(lambda: "0.080566 V" in page.text("formulaTestResult"))
    page.click("formulaSaveButton")
    page.wait_for(lambda: not page.visible("formulaDialog"))
    assert running.h.services.annotations.formula("GPIO.PA_DOUT.DOUT") == ("x * 3.3 / 4096", "V")


@pytest.mark.req("16.dialog")
def test_generate_code_opens_the_code_dialog(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.click("actionsCodeButton")
    ui.wait_for(lambda: ui.visible("codeDialog"))
    assert "Generated code from SiRAT Actions" in ui.find("codeText").property("text") or \
        "Generated" in ui.find("codeText").property("text")
    ui.click("codeCloseButton")
    ui.wait_for(lambda: not ui.visible("codeDialog"))


@pytest.mark.req("35.search")
def test_search_the_log_panel(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.click("logSearchField")
    for ch in "CONNECTED":
        ui._key(0, ch)
    log = running.h.shell.log
    ui.wait_for(lambda: log.searchText == "CONNECTED")
    assert log.matchText == "2 of 2"  # "Connected to DUT 1 (EFR32)" and "Connected to DUT 1 · EFR32XG29…"
    ui.click("logNextMatch")
    assert log.matchText == "1 of 2"


@pytest.mark.req("plan.palette")
def test_ctrl_k_jumps_to_a_register(running, qtbot):
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    QTest.keyClick(running.window, Qt.Key_K, Qt.ControlModifier)
    ui.wait_for(lambda: ui.visible("commandPalette"))
    ui.wait_for(lambda: ui.find("paletteField").property("activeFocus"))
    for ch in "lpmode":
        ui._key(0, ch)
    ui.wait_for(lambda: running.h.shell.palette.results.count > 0)
    ui._key(Qt.Key_Return, "\r")
    ui.wait_for(lambda: not ui.visible("commandPalette"))
    assert running.h.shell.currentPage == "registers"
    assert ui.text("detailTitle") == "BUFC.LPMODE"


@pytest.mark.req("4.read-all-progress")
def test_read_all_dialog_shows_and_cancels(running, qtbot):
    ui = Ui(running.app, qtbot)
    running.h.fake.set_latency("registers.read", 40)
    running.h.shell.tree.readAll([r["name"] for r in running.h.shell.tree.model.items].index("BUFC"))
    ui.wait_for(lambda: ui.visible("readAllDialog"))
    assert ui.text("readAllCount") == "1 of 9"
    ui.click("readAllCancelButton")
    running.h.scheduler.advance(40)
    ui.wait_for(lambda: not ui.visible("readAllDialog"))


@pytest.mark.req("32.validate")
def test_hardware_config_validation_in_the_real_page(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("settings")
    ui.wait_for(lambda: ui.exists("hwPortField"))
    assert ui.enabled("hwPortField") is False  # off until "Use a specific RPC address" is checked
    ui.click("hwOverrideBox")
    ui.wait_for(lambda: ui.enabled("hwPortField"))
    ui.click("hwPortField")
    for ch in "99999":
        ui._key(0, ch)
    ui.wait_for(lambda: ui.find("hwPortField").property("invalid") is True)
    assert ui.enabled("hwSaveButton") is False
    ui.click("hwTimeoutField")  # leave the field, then come back: the click selects the old value
    ui.click("hwPortField")
    for ch in "10002":
        ui._key(0, ch)
    ui.wait_for(lambda: ui.enabled("hwSaveButton"))
    ui.click("hwSaveButton")
    ui.wait_for(lambda: ui.text("hwStatus") == "Configuration saved successfully!")


@pytest.mark.req("31.info")
def test_system_info_tabs_in_the_real_page(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("settings")
    ui.wait_for(lambda: ui.exists("segment_RPC Information"))
    ui.click("segment_RPC Information")
    assert running.h.shell.systemInfo.tabIndex == 2
    assert {r["key"] for r in running.h.shell.systemInfo.currentRows} == {"Host", "Port", "Timeout"}


@pytest.mark.req("34.load")
def test_load_a_session_from_the_browser(running, qtbot):
    ui = Ui(running.app, qtbot)
    running.h.services.sessions.save("demo session")
    running.h.services.favorites.remove("MODEM.CTRL")
    ui.navigate("settings")
    ui.wait_for(lambda: ui.exists("loadSessionButton"))
    ui.click("loadSessionButton")
    ui.wait_for(lambda: ui.visible("sessionBrowser"))
    ui.wait_for(lambda: ui.exists("sessionRow_demo session"))
    ui.click("sessionRow_demo session")
    ui.click("sessionLoadButton")
    ui.wait_for(lambda: ui.visible("confirmDialog"))
    ui.click("confirmAcceptButton")
    ui.wait_for(lambda: not ui.visible("sessionBrowser"))
    assert "MODEM.CTRL" in running.h.services.favorites.names


@pytest.mark.req("12.take")
def test_take_a_dump_then_diff_it_against_live_values(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("dumps")
    ui.wait_for(lambda: ui.exists("takeDumpButton") and ui.enabled("takeDumpButton"))
    ui.click("takeDumpButton")
    ui.wait_for(lambda: ui.visible("dumpPicker"))
    ui.click("dumpPeripheral_BUFC")
    ui.click("dumpStartButton")
    ui.wait_for(lambda: ui.visible("promptDialog"))
    ui.click("promptSubmitButton")
    ui.wait_for(lambda: ui.exists("dump_dump") and not ui.visible("promptDialog"))

    running.h.select("BUFC.LPMODE")
    running.h.shell.detail.write("0x3")
    ui.click("dump_dump")
    ui.wait_for(lambda: ui.enabled("diffLiveButton"))
    ui.click("diffLiveButton")
    ui.wait_for(lambda: ui.exists("diff_BUFC.LPMODE"))
    assert ui.text("comparisonSummary").startswith("1 register differs")


@pytest.mark.req("21.compare")
def test_radio_calculator_diff_from_the_dumps_page(running, qtbot):
    from pathlib import Path
    ui = Ui(running.app, qtbot)
    sample = Path(__file__).resolve().parents[2] / "docs" / "samples" / "PHY_demo.cfg"
    running.h.container.dialogs.choose_open_file = lambda title, filters: str(sample)  # instead of the Windows dialog
    ui.navigate("dumps")
    ui.wait_for(lambda: ui.exists("radioDiffButton") and ui.enabled("radioDiffButton"))
    ui.click("radioDiffButton")
    ui.wait_for(lambda: ui.visible("dumpPicker"))
    ui.click("dumpPeripheral_USART0")  # uncheck it
    ui.click("dumpStartButton")
    ui.wait_for(lambda: ui.exists("radio_MODEM.CTRL.DEMODSEL")
                and not ui.visible("dumpPicker") and not ui.visible("dumpProgressDialog"))
    assert ui.text("comparisonSummary") == "\u2713 7 Matches | \u26A0 2 Mismatches | \u274C 1 Errors"
    ui.click("radioSort_status")
    ui.wait_for(lambda: running.h.shell.dumps.sortColumn == "status")
    ui.click("comparisonHelp")  # click keeps the explanation open
    ui.wait_for(lambda: ui.visible("comparisonHelpPopup"))
    assert "Mismatch" in ui.find("comparisonHelpPopup").property("contentItem").property("text")


@pytest.mark.req("24.apply")
def test_route_a_prs_signal_then_remove_it(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("radio")
    ui.wait_for(lambda: ui.exists("prsApplyButton") and ui.enabled("prsApplyButton"))
    ui.click("prsApplyButton")
    ui.wait_for(lambda: ui.exists("prsRemove_PA0"))
    ui.click("prsRemove_PA0")
    ui.wait_for(lambda: running.h.shell.prs.routes.count == 0)
    assert running.h.services.history.entries[-1].target == "GPIO.PORTA_MODEL.MODE0"


def _popout(key):
    from PyQt5.QtGui import QGuiApplication
    return next((w for w in QGuiApplication.topLevelWindows()
                 if w.objectName() == f"popout_{key}" and w.isVisible()), None)


def _in_window(window, name):
    stack = [window.contentItem()]
    while stack:
        item = stack.pop()
        if item.objectName() == name:
            return item
        stack.extend(item.childItems())
    return None


@pytest.mark.req("ui.popout")
def test_right_click_a_nav_tab_to_open_the_page_in_its_own_window(running, qtbot):
    from PyQt5.QtCore import QPointF, Qt
    from PyQt5.QtTest import QTest
    ui = Ui(running.app, qtbot)
    nav = ui.find("nav_watch")
    center = nav.mapToScene(QPointF(nav.width() / 2, nav.height() / 2)).toPoint()
    QTest.mouseClick(ui.window, Qt.RightButton, Qt.NoModifier, center)
    ui.wait_for(lambda: ui.visible("navMenuPopOut_watch"))
    ui.click("navMenuPopOut_watch")
    ui.wait_for(lambda: _popout("page:watch") is not None)
    ui.wait_for(lambda: _in_window(_popout("page:watch"), "watchList") is not None)
    assert ui.visible("navPopped_watch")
    ui.navigate("watch")
    ui.wait_for(lambda: ui.visible("pagePlaceholder_watch"))
    ui.click("placeholderDock")
    ui.wait_for(lambda: _popout("page:watch") is None)
    ui.wait_for(lambda: ui.visible("watchList"))


@pytest.mark.req("ui.popout")
def test_pop_out_the_watch_list_the_logger_and_one_graph(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("watchPopOutButton"))
    ui.click("watchPopOutButton")
    ui.wait_for(lambda: _popout("watchList") is not None and ui.visible("watchListPlaceholder"))
    ui.click("loggerPopOutButton")
    ui.wait_for(lambda: _popout("logger") is not None and ui.visible("loggerPlaceholder"))
    running.h.shell.windows.close("logger")
    ui.wait_for(lambda: ui.exists("seriesPopOut_SYNTH.FREQ.FREQ") and ui.visible("seriesPopOut_SYNTH.FREQ.FREQ"))
    ui.click("seriesPopOut_SYNTH.FREQ.FREQ")
    ui.wait_for(lambda: _popout("graph:SYNTH.FREQ.FREQ") is not None)
    window = _popout("graph:SYNTH.FREQ.FREQ")
    ui.wait_for(lambda: _in_window(window, "graphPlot_SYNTH.FREQ.FREQ") is not None)
    assert ui.visible("graphPlaceholder_SYNTH.FREQ.FREQ") and not ui.visible("plot_SYNTH.FREQ.FREQ")
    window.close()
    ui.wait_for(lambda: running.h.shell.windows.openKeys == ["watchList"])
    ui.wait_for(lambda: ui.visible("plot_SYNTH.FREQ.FREQ"))
