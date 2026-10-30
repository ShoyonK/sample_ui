"""End-to-end user journeys through the real QML window (docs/FRONTEND_PLAN.md section 7.5)."""

import pytest
from PyQt5.QtCore import Qt
from pages import Dialogs, RegistersPage, Ui
from sirat_ui.domains.shell.pages import PAGES as PAGE_TABLE

PAGES = [p["key"] for p in PAGE_TABLE]   # a new page row is load-tested without touching this file


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
    ui.wait_for(lambda: ui.exists("segment_Live"))
    assert not ui.visible("watchAddSelectedButton")  # selection actions only while rows are selected
    ui.click("segment_Live")
    running.h.scheduler.advance(2000)
    ui.settle()
    assert running.h.shell.watch.live
    assert ui.exists("watchRow_SYNTH.FREQ.FREQ")
    ui.click("segment_Live")  # already live: nothing changes
    assert running.h.shell.watch.live
    ui.click("segment_Paused")
    ui.wait_for(lambda: not running.h.shell.watch.live)


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
    moon = ui.find("themeButton").property("iconColor")
    ui.click("themeButton")
    assert running.h.shell.state.darkMode is True
    ui.wait_for(lambda: ui.find("themeButton").property("iconName") == "sun")
    sun = ui.find("themeButton").property("iconColor")
    assert sun != moon and sun.red() > sun.green() > sun.blue()    # warm, not the grey of the other icon buttons
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
    running.h.container.dialogs.choose_open_file = lambda *_: str(sample)  # instead of the Windows dialog
    ui.navigate("dumps")
    ui.wait_for(lambda: ui.exists("radioDiffButton") and ui.enabled("radioDiffButton"))
    ui.click("radioDiffButton")
    ui.wait_for(lambda: ui.visible("dumpPicker"))
    ui.click("dumpPeripheral_USART0")  # uncheck it
    ui.click("dumpStartButton")
    ui.wait_for(lambda: ui.exists("radio_MODEM.CTRL.DEMODSEL")
                and not ui.visible("dumpPicker") and not ui.visible("dumpProgressDialog"))
    assert running.h.shell.comparison.resultSummary == "\u2713 7 Matches | \u26A0 2 Mismatches | \u274C 1 Errors"
    assert [ui.text(n) for n in ("radioMatchCount", "radioMismatchCount", "radioErrorCount")] == \
        ["7 matches", "2 mismatches", "1 error"]
    ui.click("radioSort_status")
    ui.wait_for(lambda: running.h.shell.comparison.sortColumn == "status")
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
    ui.wait_for(lambda: ui.find("navMenu_watch").property("opened"))
    ui.settle(300)    # a click in the instant the menu opens can be dropped; no person is that fast
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


def test_hide_the_dock_to_a_strip_and_bring_it_back(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.wait_for(lambda: ui.visible("dockHideButton"))
    ui.click("dockHideButton")
    ui.wait_for(lambda: ui.visible("dockToggle") and not ui.visible("dockHideButton"))
    ui.navigate("dumps")                       # other pages keep their own setting
    ui.wait_for(lambda: ui.visible("dockHideButton"))
    ui.navigate("watch")                       # Watch starts with the strip
    ui.wait_for(lambda: ui.visible("dockLogSegment"))
    ui.click("dockLogSegment")
    ui.wait_for(lambda: ui.visible("dockHideButton"))
    ui.navigate("registers")
    ui.wait_for(lambda: ui.visible("dockToggle") and not ui.visible("dockHideButton"))
    ui.click("dockToggle")
    ui.wait_for(lambda: ui.visible("dockHideButton"))


def test_instruments_apply_the_signal_generator_and_capture_on_the_eca(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("instruments")
    ui.wait_for(lambda: ui.exists("sgApplyButton") and ui.enabled("sgApplyButton"))
    ui.click("sgApplyButton")
    ui.wait_for(lambda: ui.text("sgStatus") == "Configuration applied")
    ui.click("segment_RF on")
    ui.wait_for(lambda: running.h.fake.bench.rf_on)
    ui.click("rfConnectButton")
    ui.wait_for(lambda: ui.text("rfCurrent") == "DUT 1 is on TX_PATH")
    flick = ui.find("page_instruments").property("item").property("contentItem")   # scroll down to the ECA card
    flick.setProperty("contentY", max(0, flick.property("contentHeight") - flick.property("height")))
    ui.settle(100)
    ui.click("ecaCaptureButton")
    running.h.scheduler.advance(2000)                  # the fake's capture steps run on test time
    ui.wait_for(lambda: ui.exists("ecaPlot_PA_EN") and ui.exists("ecaMeasure_RX_EN"), timeout=8000)
    assert not ui.visible("ecaEmpty")


def test_instruments_chamber_shows_the_live_reading(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("instruments")
    ui.wait_for(lambda: ui.exists("chActual") and ui.text("chActual") == "23.0 °C")
    assert ui.text("chTrend") == "Stable"


def _output(vm) -> str:
    return "\n".join(r["text"] for r in vm.output.items)


def test_advanced_console_and_custom_function_share_variables(running, qtbot):
    ui = Ui(running.app, qtbot)
    shell = running.h.shell
    ui.navigate("advanced")
    ui.wait_for(lambda: ui.visible("consoleInputArea"))
    ui.type_text("consoleInputArea", "x = 6 * 7")
    ui.type_text("consoleInputArea", "x")
    ui.wait_for(lambda: "\n42" in _output(shell.pyConsole))
    ui._key(Qt.Key_Up, "")                                  # history: back to the last command
    ui.wait_for(lambda: ui.text("consoleInputArea") == "x")

    running.h.services.functions.create("double_x")
    running.h.services.functions.set_code("double_x", "return x * 2\n")
    ui.click("segment_Custom functions")
    ui.click("function_double_x")
    ui.wait_for(lambda: ui.enabled("functionRunButton"))
    ui.click("functionRunButton")
    ui.wait_for(lambda: "84" in _output(shell.customFunctions))


def test_advanced_dut_control_executes_a_method(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("advanced")
    ui.click("segment_DUT control")
    ui.wait_for(lambda: ui.exists("api_LPW"))
    ui.click("api_LPW")
    ui.click("api_lpw.radio")
    ui.click("api_lpw.radio.SetPower")
    ui.wait_for(lambda: ui.visible("param_power_dbm"))
    ui.type_text("param_power_dbm", "5", enter=False)
    ui.wait_for(lambda: ui.enabled("apiExecuteButton"))
    ui.click("apiExecuteButton")
    ui.wait_for(lambda: "Result (float): 5.0" in _output(running.h.shell.dutControl))


def test_advanced_memory_read_and_confirmed_write(running, qtbot):
    ui, dialogs = Ui(running.app, qtbot), Dialogs(running.app, qtbot)
    ui.navigate("advanced")
    ui.click("segment_Memory")
    ui.wait_for(lambda: ui.enabled("memoryReadButton"))
    ui.click("memoryReadButton")
    ui.wait_for(lambda: running.h.shell.memory.rows.count == 16)
    assert "SiRAT fake RAM" in running.h.shell.memory.rows.items[0]["ascii"]
    ui.click("segment_DWords")
    ui.type_text("memoryWriteValueField", "0x12345678", enter=False)
    ui.click("memoryWriteButton")
    ui.wait_for(dialogs.confirm_open)
    dialogs.accept_confirm()
    ui.wait_for(lambda: running.h.shell.memory.rows.items[0]["cells"][0] == {"t": "0x12345678", "c": True})


def test_recover_a_faulted_dut_from_the_top_bar(running, qtbot):
    ui, dialogs = Ui(running.app, qtbot), Dialogs(running.app, qtbot)
    assert not ui.visible("recoverButton")
    op = {"type": "dut_control_method", "method_path": "lpw.radio.SetPower", "method_name": "SetPower",
          "params": {"power_dbm": 30}}                  # the fake DUT asserts: a hardware error mid-run
    action = running.h.services.actions.add("fault_journey", [op])
    running.h.services.actions.run([action.name])
    running.h.scheduler.advance(2000)
    ui.wait_for(lambda: ui.visible("recoverButton") and ui.text("connectionPill") == "Fault")
    ui.click("recoverButton")
    ui.wait_for(dialogs.confirm_open)
    dialogs.accept_confirm()
    ui.wait_for(lambda: not ui.visible("recoverButton") and ui.text("connectionPill") == "Connected")


def test_right_clicking_a_nav_tab_stays_on_the_current_page(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.right_click("nav_dumps")
    ui.wait_for(lambda: ui.visible("navMenuPopOut_dumps"))
    assert running.h.shell.currentPage == "watch"


def test_right_clicking_a_segment_does_not_pick_it(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("advanced")
    ui.wait_for(lambda: ui.exists("segment_Memory"))
    ui.right_click("segment_Memory")
    assert running.h.shell.advanced.tab == 0


def test_start_buttons_are_red_until_they_are_running(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("loggerRecordButton"))
    assert ui.find("loggerRecordButton").property("variant") == "run"

    live = ui.find("segment_Live")
    assert live.property("inviting") is True
    ui.click("segment_Live")
    ui.wait_for(lambda: running.h.shell.watch.live)
    assert live.property("inviting") is False


def test_a_running_logger_swaps_start_for_a_stop_button(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("loggerRecordButton"))
    running.h.shell.logger.toggleRecording()
    ui.wait_for(lambda: ui.find("loggerRecordButton").property("variant") == "danger")
    assert ui.text("loggerRecordButton") == "Stop"


@pytest.mark.parametrize("page, button", [("actions", "actionsRunSelectedButton"), ("sequences", "runSequenceButton"),
                                          ("instruments", "ecaCaptureButton"), ("instruments", "sgInfiniteButton")])
def test_each_run_button_uses_the_run_style(running, qtbot, page, button):
    ui = Ui(running.app, qtbot)
    ui.navigate(page)
    ui.wait_for(lambda: ui.exists(button))
    assert ui.find(button).property("variant") == "run"


def _active_popout(ui, qtbot, key):
    window = _popout(key)
    window.requestActivate()
    qtbot.waitUntil(window.isActive, timeout=2000)
    return window


def _click_in(window, item, qtbot):
    from PyQt5.QtCore import QPointF, Qt
    from PyQt5.QtTest import QTest
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center)
    qtbot.wait(150)


@pytest.mark.req("ui.popout")
def test_a_popped_out_dumps_page_opens_its_dialogs_in_its_own_window(running, qtbot):
    ui = Ui(running.app, qtbot)
    running.h.shell.windows.open("page", "dumps")
    ui.wait_for(lambda: _popout("page:dumps") is not None
                and _in_window(_popout("page:dumps"), "takeDumpButton") is not None)
    window = _active_popout(ui, qtbot, "page:dumps")
    picker = ui.find("dumpPicker")
    ui.wait_for(lambda: picker.property("parent").window() is window)

    _click_in(window, _in_window(window, "takeDumpButton"), qtbot)
    ui.wait_for(lambda: picker.property("opened"))
    assert picker.property("parent").window() is window

    # It stays put while open, even if the main window gets used
    ui.window.requestActivate()
    qtbot.waitUntil(ui.window.isActive, timeout=2000)
    qtbot.wait(100)
    assert picker.property("parent").window() is window
    running.h.shell.dumpPicker.closePicker()

    # Closing the pop-out brings dialogs home
    ui.wait_for(lambda: not picker.property("visible"))
    running.h.shell.windows.close("page:dumps")
    ui.wait_for(lambda: _popout("page:dumps") is None)
    ui.wait_for(lambda: picker.property("parent") is not None and picker.property("parent").window() is ui.window)


def test_clicking_another_page_stops_the_watch_and_the_logger(running, qtbot):
    ui = Ui(running.app, qtbot)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.exists("loggerRecordButton") and ui.enabled("loggerRecordButton"))
    ui.click("loggerRecordButton")
    ui.click("segment_Live")
    ui.wait_for(lambda: ui.text("loggerRecordButton") == "Stop" and running.h.shell.watch.live)
    ui.navigate("registers")
    ui.wait_for(lambda: not running.h.shell.watch.live and not running.h.services.logger.recording)
    ui.navigate("watch")
    ui.wait_for(lambda: ui.text("loggerRecordButton") == "Start")
    assert ui.find("segment_Live").property("inviting") is True
