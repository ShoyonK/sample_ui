"""Settings: export/import/clear (req 2), About (req 2), hardware configuration (req 32), system info (req 31)."""

import datetime as dt
import json

import pytest

from sirat_ui.domains.connection.system_info import copy_text
from sirat_ui.gateway.errors import ErrorCode
from sirat_ui.models.station import RpcAddress


# ---- export / import / clear (req 2) ---------------------------------------------------------

@pytest.mark.req("2.export-import")
def test_export_then_import_restores_settings_live(harness, tmp_path):
    bundle = tmp_path / "bundle.json"
    harness.ix.answer_save(str(bundle))
    harness.shell.settings.exportSettings()
    data = json.loads(bundle.read_text())
    assert data["format"] == "sirat-user-settings"
    assert data["files"]["favorites"] == {"favorites": ["MODEM.CTRL", "CMU.CLKEN0", "SYNTH.FREQ", "BUFC.LPMODE"]}

    harness.services.favorites.remove("MODEM.CTRL")
    harness.services.actions.remove("lpmode_on")
    harness.ix.answer_open(str(bundle))
    harness.ix.answer_next(True)  # confirm the overwrite
    harness.shell.settings.importSettings()
    assert "MODEM.CTRL" in [r["fullName"] for r in harness.shell.favorites.model.items]
    assert "lpmode_on" in [r["name"] for r in harness.shell.actions.model.items]
    assert harness.ix.toasts[-1] == ("success", "Imported 13 settings files")


def test_import_asks_first_and_can_be_declined(harness, tmp_path):
    bundle = tmp_path / "bundle.json"
    harness.ix.answer_save(str(bundle))
    harness.shell.settings.exportSettings()
    harness.services.favorites.remove("MODEM.CTRL")
    harness.ix.answer_open(str(bundle))
    harness.ix.answer_next(False)
    harness.shell.settings.importSettings()
    assert harness.ix.confirms[-1].title == "Import user settings"
    assert "MODEM.CTRL" not in harness.services.favorites.names


def test_import_rejects_files_that_are_not_exports(harness, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"hello": 1}')
    harness.ix.answer_open(str(bad))
    harness.ix.answer_next(True)
    harness.shell.settings.importSettings()
    assert harness.ix.toasts[-1] == ("error", "bad.json isn't a SiRAT settings export")


@pytest.mark.req("2.clear")
def test_clear_all_resets_every_settings_file_after_confirming(harness):
    harness.shell.state.toggleDarkMode()
    harness.ix.answer_next(True)
    harness.shell.settings.clearAllSettings()
    assert harness.services.favorites.names == []
    assert harness.shell.favorites.visible is False
    assert list(harness.services.actions.actions) == []
    assert harness.shell.watch.model.count == 0
    assert harness.shell.state.darkMode is False
    assert json.loads((harness.home / ".sirat_favorites.json").read_text()) == {"favorites": []}


# ---- About ----------------------------------------------------------------------------------

def test_about_shows_versions_and_the_station(harness):
    rows = {r["key"]: r["value"] for r in harness.shell.settings.aboutRows}
    assert rows["SiRAT"] == "0.1.0" and rows["Station service"] == "fake-2026.10" and rows["Protocol"] == "1"
    assert rows["Python"].startswith("3.10")


# ---- Hardware configuration (req 32) -----------------------------------------------------------

@pytest.mark.req("32.validate")
def test_hardware_inputs_are_validated_and_save_is_disabled(harness):
    hw = harness.shell.hardware
    assert hw.canSave and (hw.host, hw.port, hw.timeout, hw.position) == ("localhost", "10001", "5", "1")
    assert hw.override is False
    hw.setOverride(True)  # host and port are only checked when they'll be used
    hw.setField("port", "70000")
    hw.setField("host", "  ")
    hw.setField("timeout", "abc")
    hw.setField("position", "5")
    assert set(hw.errors) == {"host", "port", "timeout", "position"}
    assert hw.errors["port"] == "Port must be between 1 and 65535"
    assert hw.canSave is False
    hw.save()
    assert harness.fake.calls_to("dut.set_rpc_timeout") == []


@pytest.mark.req("32.save")
def test_hardware_save_writes_the_original_file_and_applies_timeout(harness):
    hw = harness.shell.hardware
    hw.setOverride(True)
    hw.setField("host", "192.168.1.100")
    hw.setField("timeout", "12")
    hw.setField("position", "2")
    hw.save()
    saved = json.loads((harness.home / ".sirat" / "hardware_config.json").read_text())
    assert saved == {"rpc_host": "192.168.1.100", "rpc_port": 10001, "rpc_timeout": 12, "dut_position": 2,
                     "rpc_override": True}
    assert harness.fake.rpc_timeout_s == 12 and harness.shell.state.position == 2
    assert hw.statusText == "Configuration saved successfully!" and hw.statusLevel == "ok"
    assert harness.restart().shell.hardware.host == "192.168.1.100"


@pytest.mark.req("32.test")
def test_test_connection_does_not_keep_a_new_connection(harness):
    hw = harness.shell.hardware
    hw.setField("position", "3")  # DUT 3 isn't connected
    hw.testConnection()
    assert hw.statusText.startswith("Connection successful!") and "DUT 3" in hw.statusText
    assert harness.fake.facts[3].dut_connected is False
    assert harness.fake.facts[1].dut_connected is True  # the existing connection is untouched


def test_test_connection_reports_failures(harness):
    harness.fake.fail_next("dut.probe", ErrorCode.INVALID_PARAMS, "rpc.host must not be empty")
    hw = harness.shell.hardware
    hw.setField("position", "2")
    hw.testConnection()
    assert hw.statusText == "Connection failed: rpc.host must not be empty" and hw.statusLevel == "danger"


@pytest.mark.req("32.test")
def test_testing_a_position_in_use_keeps_its_connection(harness):
    """dut.probe never connects or disconnects, so testing DUT 1 while it's connected is safe."""
    hw = harness.shell.hardware
    hw.testConnection()
    assert hw.statusText.startswith("Connection successful!") and harness.state.connected
    assert harness.fake.calls_to("dut.disconnect") == [] and len(harness.fake.calls_to("dut.connect")) == 1


# ---- System information (req 31) ----------------------------------------------------------------

@pytest.mark.req("31.info")
def test_system_info_shows_four_categories(harness):
    info = harness.shell.systemInfo
    assert info.tabTitles == ["Chip Information", "Device Information", "RPC Information", "Firmware/Application"]
    assert {r["key"]: r["value"] for r in info.currentRows}["Part Number"].startswith("EFR32XG29XFULL")
    info.setTabIndex(1)
    rows = {r["key"]: r["value"] for r in info.currentRows}
    assert rows["Flash Size"] == "1024 KB" and rows["Unique ID"] == "0x0123456789ABCDF0"


@pytest.mark.req("31.auto-refresh")
def test_system_info_refreshes_when_a_dut_connects(disconnected):
    info = disconnected.shell.systemInfo
    assert info.currentRows == [] and "not connected" in info.statusText
    disconnected.shell.connection.connect()
    assert info.currentRows and "EFR32XG29XFULL" in info.statusText


def test_system_info_copy_all_uses_the_req_31_format(harness):
    calls = []
    harness.fake.dut_info(1).then(calls.append)
    text = copy_text(calls[0], now=dt.datetime(2026, 10, 27, 14, 23, 45))
    assert text.startswith("=== SiRAT System Information ===\nGenerated: 2026-10-27 14:23:45\n--- Chip Information ---\n")
    assert "Flash Size: 1024 KB" in text and "Timeout: 5.0 seconds" in text
    harness.shell.systemInfo.copyAll()
    assert harness.ix.toasts[-1] == ("info", "System information copied")



# ---- RPC address override (docs/API_DESIGN.md, dut.connect / dut.probe) ----------------------------

@pytest.mark.req("32.address")
def test_without_the_override_host_and_port_are_not_sent_or_checked(harness):
    hw = harness.shell.hardware
    hw.setField("port", "not a port")
    assert "port" not in hw.errors and hw.canSave  # unused fields don't block Save
    hw.setField("position", "2")
    hw.testConnection()
    call = harness.fake.calls_to("dut.probe")[-1]
    assert call.params["rpc"] is None and call.params["pos"] == 2


@pytest.mark.req("32.address")
def test_with_the_override_test_connection_uses_the_address(harness):
    hw = harness.shell.hardware
    hw.setOverride(True)
    hw.setField("host", "192.168.1.50")
    hw.setField("port", "10005")
    hw.setField("position", "2")
    hw.testConnection()
    call = harness.fake.calls_to("dut.probe")[-1]
    assert call.params["rpc"] == RpcAddress("192.168.1.50", 10005)
    assert "192.168.1.50:10005" in hw.statusText


def test_an_unreachable_override_reports_a_timeout(harness):
    hw = harness.shell.hardware
    hw.setOverride(True)
    hw.setField("host", "bench7.invalid")
    hw.setField("position", "2")
    hw.testConnection()
    assert hw.statusText == "Connection failed: No answer from bench7.invalid:10001 within 5 s"


@pytest.mark.req("3.address")
def test_connect_sheet_starts_from_settings_and_overrides_one_connection(disconnected):
    h = disconnected
    h.services.hardware.save(__import__("sirat_ui.domains.settings.hardware", fromlist=["HardwareConfig"])
                             .HardwareConfig("192.168.1.77", 10002, 5, 1, rpc_override=True))
    sheet = h.shell.connection
    sheet.openSheet()
    assert (sheet.override, sheet.rpcHost, sheet.rpcPort) == (True, "192.168.1.77", "10002")
    sheet.setRpcHost("192.168.1.88")  # this connection only
    sheet.connect()
    call = h.fake.calls_to("dut.connect")[-1]
    assert call.params["rpc"] == RpcAddress("192.168.1.88", 10002)
    assert h.services.hardware.config.rpc_host == "192.168.1.77"  # Settings unchanged
    assert {r["key"]: r["value"] for r in h.shell.systemInfo.sections[2]["rows"]}["Host"] == "192.168.1.88"


def test_connect_sheet_without_override_uses_the_workspace_config(disconnected):
    sheet = disconnected.shell.connection
    sheet.openSheet()
    assert sheet.override is False
    sheet.connect()
    call = disconnected.fake.calls_to("dut.connect")[-1]
    assert call.params["rpc"] is None


def test_connect_sheet_rejects_a_bad_address_before_sending(disconnected):
    sheet = disconnected.shell.connection
    sheet.openSheet()
    sheet.setOverride(True)
    sheet.setRpcPort("99999")
    sheet.connect()
    assert disconnected.fake.calls_to("dut.connect") == []
    assert "between 1 and 65535" in disconnected.ix.toasts[-1][1]


def test_reconnect_after_a_drop_is_rpc_only_and_keeps_the_address(disconnected):
    """Req 3 recovery: dut.reconnect redoes only the RPC link, at the address the DUT was reached on."""
    sheet = disconnected.shell.connection
    sheet.openSheet()
    sheet.setOverride(True)
    sheet.setRpcHost("192.168.1.99")
    sheet.connect()
    disconnected.fake.drop_dut(1)
    disconnected.shell.recovery.reconnect()
    assert len(disconnected.fake.calls_to("dut.connect")) == 1          # no second bench setup
    assert len(disconnected.fake.calls_to("dut.reconnect")) == 1 and disconnected.state.connected
    assert disconnected.fake.addresses[1] == ("192.168.1.99", 10001)
