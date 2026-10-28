"""Pydantic validation of files read from disk (stores/schemas): keep valid entries, report and skip the rest."""

import json

import pytest
from support import Harness

from sirat_ui.stores.schemas import CLEANERS, Report, clean_session, validate_operation


def clean(name, raw):
    report = Report(name)
    return CLEANERS[name](raw, report), [str(p) for p in report.problems]


# ---- actions ---------------------------------------------------------------------------------------

def test_valid_actions_pass_and_hex_strings_become_numbers():
    data, problems = clean("actions", {
        "a": {"operations": [{"register": "MODEM.CTRL", "value": "0x1F"}], "enabled": False},
        "legacy_list": [{"register": "BUFC.LPMODE", "value": 3}],
        "legacy_dict": {"CMU.CLKEN0": 7},
    })
    assert problems == []
    assert data["a"] == {"operations": [{"register": "MODEM.CTRL", "value": 31}], "enabled": False}
    assert data["legacy_list"]["operations"] == [{"register": "BUFC.LPMODE", "value": 3}]
    assert data["legacy_dict"] == {"operations": [{"register": "CMU.CLKEN0", "value": 7}], "enabled": True}


def test_an_action_with_a_bad_operation_is_skipped_whole_and_reported():
    data, problems = clean("actions", {
        "good": {"operations": [{"register": "MODEM.CTRL", "value": 1}]},
        "bad": {"operations": [{"register": "MODEM.CTRL", "value": 1},
                               {"register": "MODEM.CTRL", "value": "twelve"}]},
    })
    assert list(data) == ["good"]
    assert problems == ["actions: bad.operations.1: register_write: value: 'twelve' isn't a number "
                        "(use decimal or 0x hex)"]


@pytest.mark.parametrize("op, message", [
    ({"type": "prs_route", "signal": "FRAMEDET", "pin": "PC0", "channel": 2}, "Ports A/B can only use"),
    ({"type": "prs_route", "signal": "FRAMEDET", "pin": "PE0", "channel": 2}, "pin"),
    ({"type": "rf_switch", "path": "TX", "dut_position": 9}, "dut_position"),
    ({"type": "signal_generator", "sg_type": "PacketSrw", "frequency_mhz": -1, "power_dbm": 0}, "frequency_mhz"),
    ({"type": "load_wifi_phy", "config": {"mode": "RX", "standard": "802.11a", "channel": 6, "power_mode": "HP",
                                          "rate": "24", "phy_name": "WIFI_5G"}}, "channel 6 isn't available"),
    ({"type": "teleport"}, "unknown operation type 'teleport'"),
    ({"register": "MODEM", "value": 1}, "register"),
    ({"register": "MODEM.CTRL", "value": 0x1_0000_0000}, "value"),
])
def test_each_operation_type_is_checked(op, message):
    with pytest.raises(ValueError, match=message):
        validate_operation(op)


def test_unknown_keys_in_an_operation_are_kept():
    op = validate_operation({"type": "dut_reconnect", "description": "x", "added_by_newer_gui": 1})
    assert op == {"type": "dut_reconnect", "description": "x", "added_by_newer_gui": 1}


# ---- other files --------------------------------------------------------------------------------------

def test_favorites_and_watch_list_skip_bad_names_and_keep_the_rest():
    favorites, problems = clean("favorites", {"favorites": ["MODEM.CTRL", 42, "not a register"]})
    assert favorites == {"favorites": ["MODEM.CTRL"]} and len(problems) == 2
    watch, problems = clean("watch_list", {"watched_fields": ["AGC.RSSI.RSSI"], "refresh_rate": -2})
    assert watch == {"watched_fields": ["AGC.RSSI.RSSI"], "refresh_rate": 1.0}
    assert problems == ["watch_list: refresh_rate.value: Input should be greater than 0"]


def test_formulas_must_parse():
    data, problems = clean("field_formulas", {"SYNTH.FREQ.FREQ": {"formula": "x / 1000", "unit": "MHz"},
                                              "AGC.RSSI.RSSI": {"formula": "import os"}})
    assert list(data) == ["SYNTH.FREQ.FREQ"]
    assert problems[0].startswith("field_formulas: AGC.RSSI.RSSI.formula:")


def test_preferences_and_hardware_keep_valid_fields_and_default_the_rest():
    prefs, problems = clean("preferences", {"dark_mode": True, "value_format": "octal", "last_position": 9})
    assert prefs["dark_mode"] is True and prefs["value_format"] == "hex" and prefs["last_position"] == 1
    assert len(problems) == 2
    hw, problems = clean("hardware_config", {"rpc_host": "10.0.0.5", "rpc_port": 70000})
    assert hw["rpc_host"] == "10.0.0.5" and hw["rpc_port"] == 10001
    assert problems == ["hardware_config: rpc_port: Input should be less than or equal to 65535"]


def test_a_file_that_isnt_the_right_shape_is_reported():
    data, problems = clean("sequences", ["not", "a", "dict"])
    assert data == {} and problems == ["sequences: expected an object, got list; ignoring the file's contents"]


# ---- sessions ------------------------------------------------------------------------------------------

def test_session_entries_are_validated_individually():
    report = Report("s.json")
    data = clean_session({"session_name": "s", "favorites": ["MODEM.CTRL", 5],
                          "history": [{"operation": "WRITE", "register": "MODEM.CTRL", "value": "0x3"},
                                      {"operation": "erase", "register": "MODEM.CTRL", "value": 1}],
                          "dumps": [{"name": "d", "timestamp": "yesterday"}]}, report)
    assert data["favorites"] == ["MODEM.CTRL"] and data["dumps"] == []
    assert data["history"] == [{"ts": 0.0, "operation": "write", "register": "MODEM.CTRL", "field": None,
                                "value": 3, "register_value": None}]
    assert {p.where.split(".")[0] for p in report.problems} == {"favorites", "history", "dumps"}


def test_a_file_without_a_session_name_isnt_a_session():
    report = Report("x.json")
    assert clean_session({"favorites": []}, report) is None and report.problems


# ---- through the app ---------------------------------------------------------------------------------------

@pytest.mark.req("1.settings")
def test_bad_entries_at_startup_are_skipped_reported_and_backed_up(qapp, tmp_path):
    actions = tmp_path / ".sirat_actions.json"
    actions.write_text(json.dumps({"ok": [{"register": "MODEM.CTRL", "value": 1}],
                                   "broken": [{"type": "prs_route", "pin": "PA0", "channel": 9, "signal": "X"}]}))
    h = Harness(tmp_path, seed=False)
    assert list(h.services.actions.actions) == ["ok"]
    level, text = h.ix.toasts[0]
    assert level == "warning" and "Skipped 1 invalid setting in .sirat_actions.json" in text
    assert any("broken.operations.0" in line.text for line in h.services.log.lines)
    assert "broken" in json.loads((tmp_path / ".sirat_actions.json.bak").read_text())


def test_unreadable_json_falls_back_to_defaults_and_is_backed_up(qapp, tmp_path):
    (tmp_path / ".sirat").mkdir()
    (tmp_path / ".sirat" / "preferences.json").write_text("{ nope")
    h = Harness(tmp_path, seed=False)
    assert h.prefs.value.dark_mode is False
    assert (tmp_path / ".sirat" / "preferences.json.bak").read_text() == "{ nope"
    assert h.ix.toasts[0][0] == "warning"


def test_import_validates_each_file(harness, tmp_path):
    bundle = tmp_path / "export.json"
    bundle.write_text(json.dumps({"format": "sirat-user-settings", "version": 1, "files": {
        "favorites": {"favorites": ["CMU.CLKEN0", "bad name"]},
        "mystery": {},
    }}))
    names, skipped = harness.services.transfer.import_(bundle)
    assert names == ["favorites"] and harness.services.favorites.names == ["CMU.CLKEN0"]
    assert [p.where for p in skipped] == ["files.favorites.favorites.1.value", "files.mystery"]


def test_import_rejects_a_file_that_isnt_an_export(harness, tmp_path):
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"format": "something-else", "files": {}}))
    with pytest.raises(ValueError, match="isn't a SiRAT settings export"):
        harness.services.transfer.import_(other)


def test_loading_a_session_with_bad_entries_warns(harness):
    harness.ix.answer_next({"name": "s"})
    harness.shell.sessions.saveSession()
    path = harness.home / ".sirat" / "sessions" / "s.json"
    data = json.loads(path.read_text())
    data["favorites"].append("???")
    path.write_text(json.dumps(data))
    harness.shell.sessions.select(0)
    harness.ix.answer_next(True)
    harness.shell.sessions.loadSelected()
    assert harness.ix.toasts[-1] == ("warning", "Loaded session s; skipped 1 invalid entries (details in the log)")
    assert "???" not in harness.services.favorites.names
