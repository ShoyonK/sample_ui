"""What the old tool (SiRAT) saved is copied into ~/.sibench once, on the first launch (stores/legacy_import.py)."""

import json

from sibench_ui.stores.json_store import UserStores
from sibench_ui.stores.legacy_import import import_legacy_data


def old_home(tmp_path):
    (tmp_path / ".sirat_favorites.json").write_text(json.dumps({"favorites": ["MODEM.CTRL"]}))
    (tmp_path / ".sirat_sequences.json").write_text(json.dumps({"rx": {"action_names": [], "description": ""}}))
    (tmp_path / ".sirat" / "sessions").mkdir(parents=True)
    (tmp_path / ".sirat" / "field_notes.json").write_text(json.dumps({"MODEM.CTRL.OPMODE": "set by the PHY"}))
    (tmp_path / ".sirat" / "sessions" / "day 1.json").write_text("{}")
    return tmp_path


def test_the_first_launch_copies_the_old_files_and_the_stores_read_them(tmp_path):
    home = old_home(tmp_path)
    copied = import_legacy_data(home)
    assert copied == ["favorites.json", "sequences.json", "field_notes.json", "sessions"]
    stores = UserStores.in_home(home)
    assert stores.favorites.load() == {"favorites": ["MODEM.CTRL"]}
    assert "rx" in stores.sequences.load()
    assert (home / ".sibench" / "sessions" / "day 1.json").exists()
    assert (home / ".sirat_favorites.json").exists()       # the old tool keeps its files


def test_nothing_is_copied_once_sibench_has_its_own_folder(tmp_path):
    home = old_home(tmp_path)
    (home / ".sibench").mkdir()
    assert import_legacy_data(home) == []
    assert not (home / ".sibench" / "favorites.json").exists()


def test_a_home_without_old_files_gets_no_folder(tmp_path):
    assert import_legacy_data(tmp_path) == []
    assert not (tmp_path / ".sibench").exists()
