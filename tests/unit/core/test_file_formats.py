"""Settings files must stay readable by, and written for, the original SiRAT (DATA REQUIREMENTS sections)."""

import json

import pytest

from sirat_ui.stores import formats
from sirat_ui.stores.json_store import UserStores

# The examples below are copied from sirat_requirements.txt.
ORIGINAL_FAVORITES = {"favorites": ["MODEM.CTRL", "CMU.CLKEN0", "GPIO.PA_DOUT"]}
ORIGINAL_WATCH = {"watched_fields": ["MODEM.CTRL.OPERATIONAL", "AGC.GAININDEX.INDEX"], "refresh_rate": 1.0}
ORIGINAL_LOGGER = {"tracked_fields": ["MODEM.CTRL.OPERATIONAL", "AGC.GAININDEX.INDEX"], "sample_rate": 1.0}
ORIGINAL_SEQUENCES = {
    "Full BLE Stack": {"action_names": ["BLE Init", "Start Advertising", "Set Power"],
                       "description": "Complete BLE initialization sequence"},
    "WiFi Test Setup": {"action_names": ["Load WiFi PHY", "Set TX Path", "Configure SG"], "description": ""},
}


@pytest.mark.req("8.persist")
def test_favorites_round_trip_the_original_format():
    assert formats.write_favorites(formats.read_favorites(ORIGINAL_FAVORITES)) == ORIGINAL_FAVORITES


@pytest.mark.req("18.persist")
def test_watch_list_round_trips_the_original_format():
    names, rate = formats.read_watch_list(ORIGINAL_WATCH)
    assert formats.write_watch_list(names, rate) == ORIGINAL_WATCH


@pytest.mark.req("17.persist")
def test_data_logger_round_trips_the_original_format():
    names, rate = formats.read_data_logger(ORIGINAL_LOGGER)
    assert formats.write_data_logger(names, rate) == ORIGINAL_LOGGER


@pytest.mark.req("14.persist")
def test_sequences_round_trip_the_original_format_including_descriptions():
    assert formats.write_sequences(formats.read_sequences(ORIGINAL_SEQUENCES)) == ORIGINAL_SEQUENCES


def test_files_written_by_earlier_builds_still_load():
    assert formats.read_favorites(["A.B"]) == ["A.B"]
    assert formats.read_watch_list(["A.B.C"]) == (["A.B.C"], 1.0)
    assert formats.read_data_logger({"fields": ["A.B.C"], "rate_s": 0.5}) == (["A.B.C"], 0.5)
    assert formats.read_sequences({"s": ["a1", "a2"]})["s"].action_names == ["a1", "a2"]


@pytest.mark.parametrize("raw", [None, 42, "text", {"favorites": "not a list"}])
def test_garbage_files_load_as_empty(raw):
    assert formats.read_favorites(raw) == []


def test_new_stores_start_in_the_original_shapes(tmp_path):
    stores = UserStores.in_home(tmp_path)
    assert stores.favorites.load() == {"favorites": []}
    assert stores.watch_list.load() == {"watched_fields": [], "refresh_rate": 1.0}
    assert stores.data_logger.load() == {"tracked_fields": [], "sample_rate": 1.0}
    assert stores.custom_functions.load() == []


def test_app_writes_original_formats_to_disk(harness):
    harness.select("GPIO.PA_DOUT")
    harness.shell.registerShortcuts.toggleFavorite()
    harness.shell.registerShortcuts.addToWatch(harness.shell.detail.fields.get(0)["fullName"])
    harness.shell.registerShortcuts.addToLogger(harness.shell.detail.fields.get(0)["fullName"])
    harness.shell.watch.setIntervalText("2.5")
    home = harness.home
    assert "GPIO.PA_DOUT" in json.loads((home / ".sirat_favorites.json").read_text())["favorites"]
    watch = json.loads((home / ".sirat_watch_list.json").read_text())
    assert "GPIO.PA_DOUT.DOUT" in watch["watched_fields"] and watch["refresh_rate"] == 2.5
    logger = json.loads((home / ".sirat_data_logger.json").read_text())
    assert "GPIO.PA_DOUT.DOUT" in logger["tracked_fields"] and "sample_rate" in logger


def test_sequence_descriptions_survive_edits(harness):
    seqs = harness.services.sequences
    seqs.move_step("ble_rx_bringup", 0, 1)
    saved = json.loads((harness.home / ".sirat_sequences.json").read_text())
    assert saved["ble_rx_bringup"]["description"].startswith("Reconnect")
    assert saved["ble_rx_bringup"]["action_names"][1] == "reconnect_rpc"


ORIGINAL_FORMULAS = {
    "SYNTH.FREQ": {"formula": "x * 40e6 / 2**19", "unit": "Hz"},
    "TEMP.CELSIUS": {"formula": "(x - 32) * 5/9", "unit": "\u00b0C"},
}


@pytest.mark.req("11.persist")
def test_formulas_round_trip_the_original_format():
    assert formats.write_formulas(formats.read_formulas(ORIGINAL_FORMULAS)) == ORIGINAL_FORMULAS


def test_formulas_written_by_earlier_builds_still_load():
    assert formats.read_formulas({"A.B.C": ["x / 2", "V"]}) == {"A.B.C": ("x / 2", "V")}


def test_app_saves_formulas_in_the_original_format(harness):
    harness.select("GPIO.PA_DOUT")
    harness.shell.registerShortcuts.editFormula(harness.shell.detail.fields.get(0)["fullName"])
    harness.shell.formulaEditor.setExpr("x * 3.3 / 4096")
    harness.shell.formulaEditor.setUnit("V")
    harness.shell.formulaEditor.save()
    saved = json.loads((harness.home / ".sirat" / "field_formulas.json").read_text(encoding="utf-8"))
    assert saved["GPIO.PA_DOUT.DOUT"] == {"formula": "x * 3.3 / 4096", "unit": "V"}
