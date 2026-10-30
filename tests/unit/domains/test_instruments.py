"""Instruments page: signal generator (req 25), BLE packet (26), GFSK (27), RF switch (28), chamber (29), ECA (30)."""

import json

import pytest

from sirat_ui.gateway.errors import ErrorCode


# ---- signal generator (req 25) ------------------------------------------------------------------------

@pytest.mark.req("25.apply")
def test_apply_sends_hz_to_the_signal_generator_and_saves_the_settings(harness):
    sg = harness.shell.siggen
    assert sg.instrumentConnected and sg.waveforms[0] == "BLE_1M" and sg.canApply
    sg.setField("frequency", "2402")
    sg.setField("power", "-10")
    sg.apply()
    call = harness.fake.calls_to("instruments.siggen.set")[-1]
    assert call.params["id"] == "siggen1" and call.params["config"].frequency_hz == 2402e6
    assert sg.statusText == "Configuration applied"
    saved = json.loads((harness.home / ".sirat" / "signal_generator.json").read_text())
    assert saved == {"sg_type": "PacketSrw", "input_config_name": "BLE_1M", "frequency_mhz": 2402.0,
                     "power_dbm": -10.0, "overrides": {}}
    assert harness.restart().shell.siggen.frequency == "2402"


@pytest.mark.req("25.validate")
def test_out_of_range_values_block_apply(harness):
    sg = harness.shell.siggen
    sg.setField("power", "40")
    sg.setField("overrides", "nonsense")
    assert set(sg.errors) == {"power", "overrides"} and not sg.canApply
    sg.apply()
    assert harness.fake.calls_to("instruments.siggen.set") == []


@pytest.mark.req("25.trigger")
def test_triggers_and_rf_on_off(harness):
    sg = harness.shell.siggen
    assert sg.rfState == ""                     # unknown until the GUI switches it
    sg.trigger("infinite")
    sg.setRf(True)
    assert harness.fake.bench.trigger_mode == "infinite" and harness.fake.bench.rf_on
    assert (sg.triggerText, sg.rfState) == ("Infinite trigger running", "on")
    sg.trigger("single")
    sg.setRf(False)
    assert harness.fake.bench.trigger_mode == "single" and not harness.fake.bench.rf_on


@pytest.mark.req("25.load")
def test_load_from_instrument_fills_the_form(harness):
    harness.fake.bench.siggen.frequency_hz = 2480e6
    harness.fake.bench.siggen.input_config_name = "BLE_2M"
    sg = harness.shell.siggen
    sg.loadFromInstrument()
    assert (sg.frequency, sg.waveforms[sg.waveformIndex]) == ("2480", "BLE_2M")


@pytest.mark.req("25.reload")
def test_reload_waveforms_finds_new_files(harness):
    harness.fake.bench.waveform_files.append("BLE_CS_TONE")
    sg = harness.shell.siggen
    assert "BLE_CS_TONE" not in sg.waveforms
    sg.reloadWaveforms()
    assert "BLE_CS_TONE" in sg.waveforms


@pytest.mark.req("25.actions")
def test_add_to_actions_keeps_the_req_25_format_and_runs_on_the_wire(harness):
    sg = harness.shell.siggen
    sg.addToActions()
    action = harness.services.actions.actions["siggen_2440_0dbm_2"]   # the demo data already has one
    assert action.enabled is False    # Run checked shouldn't start the generator unless it's ticked
    op = action.operations[0]
    assert {k: op[k] for k in ("type", "sg_type", "input_config_name", "frequency_mhz", "power_dbm")} == \
        {"type": "signal_generator", "sg_type": "PacketSrw", "input_config_name": "BLE_1M", "frequency_mhz": 2440.0,
         "power_dbm": 0.0}
    assert "sg_role.LoadConfig(config)" in op["code"]
    harness.services.actions.run([action.name])
    wire = harness.fake.calls_to("automation.seq.run")[-1].params["ops"][0]
    assert wire["instrument_id"] == "siggen1" and wire["config"]["frequency_hz"] == 2440e6


def test_a_dropped_signal_generator_disables_the_controls_and_can_reconnect(harness):
    sg = harness.shell.siggen
    harness.fake.drop_instrument("siggen1")
    assert not sg.instrumentConnected and not sg.canApply and not sg.canControl
    assert "isn't connected" in sg.instrumentText
    sg.connectInstrument()
    assert sg.instrumentConnected and sg.canApply


# ---- RF switch (req 28) --------------------------------------------------------------------------------

@pytest.mark.req("28.connect")
def test_connect_a_path_to_a_dut_position(harness):
    rf = harness.shell.rfSwitch
    assert rf.paths[:2] == ["TX_PATH", "RX_PATH"]
    rf.setPath(1)
    rf.setPosition(1)                                   # combo index: DUT 2
    rf.connectPath()
    assert harness.fake.facts[2].rf_path == "RX_PATH"
    assert rf.currentText == "DUT 2 is on RX_PATH" and harness.ix.toasts[-1][1] == "Connected RX_PATH to DUT 2"
    rf.disconnectPath()
    assert harness.fake.facts[2].rf_path is None and not rf.canDisconnect


@pytest.mark.req("28.actions")
def test_rf_switch_action_format(harness):
    rf = harness.shell.rfSwitch
    rf.setPosition(2)
    rf.addToActions()
    assert harness.services.actions.actions["rf_tx_path"].operations == \
        [{"type": "rf_switch", "path": "TX_PATH", "dut_position": 3}]


def test_without_a_switch_the_card_says_so(harness):
    harness.fake.drop_instrument("switch1")
    rf = harness.shell.rfSwitch
    assert not rf.canConnect
    rf.connectPath()
    assert harness.fake.calls_to("rf.connect") == []


# ---- temperature chamber (req 29) ---------------------------------------------------------------------

@pytest.mark.req("29.set")
def test_set_temperature_and_watch_it_ramp_while_the_page_is_showing(harness):
    ch = harness.shell.chamber
    ch.setActive(True)
    assert (ch.actualText, ch.trendText) == ("23.0 °C", "Stable")
    ch.setField("target", "30")
    ch.setTemperature()
    harness.scheduler.advance(2100)                     # 2 °C/s, polled every 2 s
    ch.setActive(True)                                  # (re)showing the page reads at once
    assert ch.actualText == "27.0 °C" and ch.trendText == "Heating" and ch.setpointText == "Setpoint 30 °C"
    ch.setActive(False)
    reads = len(harness.fake.calls_to("instruments.chamber.read"))
    harness.scheduler.advance(10_000)
    assert len(harness.fake.calls_to("instruments.chamber.read")) == reads   # no polling while hidden


@pytest.mark.req("29.wait")
def test_wait_for_stable_reports_progress_and_finishes(harness):
    ch = harness.shell.chamber
    ch.setField("target", "25")
    ch.setTemperature()
    ch.setField("hold", "3")
    ch.waitForStable()
    assert ch.waiting and not ch.canWait and not ch.canSet          # the chamber is busy waiting
    harness.scheduler.advance(1000)
    assert "target 25 °C" in ch.waitText
    harness.scheduler.advance(5000)
    assert not ch.waiting and ch.waitText == "Stable"


def test_wait_for_stable_can_be_stopped(harness):
    ch = harness.shell.chamber
    ch.setField("target", "80")
    ch.setTemperature()
    ch.waitForStable()
    ch.abortWait()
    harness.scheduler.advance(1000)
    assert not ch.waiting and ch.waitText == "Aborted by user"


def test_chamber_inputs_are_validated(harness):
    ch = harness.shell.chamber
    ch.setField("target", "200")
    assert "target" in ch.errors and not ch.canSet


# ---- BLE and GFSK packets (req 26, req 27) ---------------------------------------------------------------

@pytest.mark.req("26.code")
def test_ble_packet_code_and_persistence(harness):
    ble = harness.shell.blePacket
    assert ble.syncWord == "0x6B7D9171"
    ble.setField("accessAddress", "0x12345678")
    ble.setField("whitening", "12")
    ble.generateCode()
    title, code = harness.ix.codes[-1]
    assert title == "BLE packet code" and "access_address=0x12345678" in code and "whitening_init=12" in code
    assert json.loads((harness.home / ".sirat" / "ble_packet.json").read_text())["access_address"] == "0x12345678"
    assert harness.restart().shell.blePacket.accessAddress == "0x12345678"


@pytest.mark.req("26.validate")
def test_ble_fields_are_validated(harness):
    ble = harness.shell.blePacket
    ble.setField("whitening", "128")
    ble.setField("crcInit", "0x1000000")
    assert set(ble.errors) == {"whitening", "crcInit"} and not ble.canGenerate


@pytest.mark.req("27.actions")
def test_gfsk_code_and_action(harness):
    g = harness.shell.gfsk
    g.setField("deviation", "500")
    g.setField("rate", "2000")
    assert g.modulationIndex == "h = 0.5"
    g.generateCode()
    assert "deviation_hz=500000" in harness.ix.codes[-1][1]
    g.addToActions()
    action = harness.services.actions.actions["gfsk_2000k_2440"]
    assert action.enabled is False
    op = action.operations[0]
    assert op["type"] == "gfsk_packet" and "GfskModulator" in op["code"]


# ---- ECA capture (req 30) --------------------------------------------------------------------------------

def _capture(harness):
    eca = harness.shell.eca
    eca.capture()
    harness.scheduler.advance(2000)
    return eca


@pytest.mark.req("30.capture")
def test_capture_downloads_plots_and_measures(harness):
    eca = harness.shell.eca
    assert eca.triggers == ["immediate", "PA_EN", "RX_EN", "PRS_CH0", "EXT"]
    assert [r["checked"] for r in eca.channels.items] == [True, True, False, False]
    assert eca.samplesText == "5,000 samples per channel"
    eca.capture()
    assert eca.capturing and not eca.canCapture
    harness.scheduler.advance(2000)
    assert eca.hasCapture and eca.progressText == "5,000 samples on 2 channels"
    assert [p["name"] for p in eca.plots.items] == ["PA_EN", "RX_EN"]
    pa = eca.measurements.items[0]
    assert (pa["frequency"], pa["highTime"], pa["edges"]) == ("800 Hz", "376.5 µs", "4")
    assert eca.markers == [0.5]                        # the trigger point


def test_large_captures_come_in_pages(harness):
    eca = harness.shell.eca
    eca.setField("rate", "20")
    eca.setField("duration", "5")                      # 100,000 samples: two pages
    _capture(harness)
    assert [c.params["offset"] for c in harness.fake.calls_to("instruments.eca.result")] == [0, 65536]
    assert eca.progressText == "100,000 samples on 2 channels"


@pytest.mark.req("30.validate")
def test_capture_limits_are_checked_before_sending(harness):
    eca = harness.shell.eca
    eca.setField("rate", "100")
    eca.setField("duration", "1000")
    assert "1,000,000" in eca.errors["duration"] and not eca.canCapture
    for row in range(2):
        eca.toggleChannel(row)
    eca.setField("duration", "1")
    assert not eca.canCapture                          # no channels picked


@pytest.mark.req("30.markers")
def test_zoom_and_markers(harness):
    eca = _capture(harness)
    eca.setField("markerA", "0.5")
    eca.setField("markerB", "1.75")
    assert eca.markerText == "B − A = 1.25 ms (800 Hz)" and eca.markers == [0.5, 0.5, 1.75]
    eca.zoom(1.0, 0.5)
    assert (eca.xMin, eca.xMax) == (0.5, 1.0)
    assert all(0.5 <= x <= 1.01 for x in eca.plots.items[0]["xs"])   # full detail inside the window
    eca.resetZoom()
    assert eca.xMin == -1


@pytest.mark.req("30.export")
def test_save_csv_with_metadata(harness, tmp_path):
    eca = _capture(harness)
    out = tmp_path / "cap.csv"
    harness.ix.answer_save(str(out))
    eca.saveCsv()
    lines = out.read_text().splitlines()
    assert lines[0] == "# SiRAT ECA capture" and "time_s,PA_EN,RX_EN" in lines
    assert len([ln for ln in lines if not ln.startswith("#")]) == 5001


def test_an_aborted_capture_keeps_the_previous_one(harness):
    eca = _capture(harness)
    eca.capture()
    eca.abort()
    harness.scheduler.advance(1000)
    assert not eca.capturing and eca.hasCapture and eca.progressText == "Aborted by user"


def test_an_instrument_drop_ends_its_capture(harness):
    eca = harness.shell.eca
    eca.capture()
    harness.fake.drop_instrument("eca1")
    assert not eca.capturing and "disconnected" in eca.progressText
    assert harness.ix.toasts[-1][0] == "error"


def test_instrument_methods_check_the_instrument_not_the_dut(disconnected):
    """Instruments work without a DUT; a capture while one runs is refused as busy (requires `idle`)."""
    eca = disconnected.shell.eca
    assert eca.canCapture
    eca.capture()
    errors = []
    disconnected.fake.eca_capture("eca1", eca.spec()).then(None, errors.append)
    assert errors[0].code == ErrorCode.WRONG_STATE and errors[0].data["missing"] == ["idle"]
