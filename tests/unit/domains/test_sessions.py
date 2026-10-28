"""Sessions (req 34): save, load, delete, preview, and the 5-minute auto-save."""

import json

import pytest

from support import Harness


def make_history(h):
    h.select("BUFC.LPMODE")
    h.shell.detail.read()
    h.shell.detail.write("0x3")


def session_names(h):
    return [r["name"] for r in h.shell.sessions.model.items]


@pytest.mark.req("34.save")
def test_save_session_writes_the_req_34_file_format(harness):
    make_history(harness)
    harness.ix.answer_next({"name": "Bring-up day 1"})
    harness.shell.sessions.saveSession()
    prompt = harness.ix.prompts[-1]
    assert prompt.fields[0].value.startswith("Session_") and "4 actions" in prompt.message
    saved = json.loads((harness.home / ".sirat" / "sessions" / "Bring-up day 1.json").read_text())
    assert set(saved) == {"session_name", "created", "modified", "dumps", "field_notes", "formulas", "actions",
                          "favorites", "history"}
    assert saved["session_name"] == "Bring-up day 1" and saved["dumps"] == []
    assert {"field": "SYNTH.FREQ.FREQ", "formula": "x / 1000", "unit": "MHz"} in saved["formulas"]
    assert [h["operation"] for h in saved["history"]] == ["read", "write"]
    assert session_names(harness) == ["Bring-up day 1"]


def test_saving_over_an_existing_name_asks_and_keeps_the_created_time(harness):
    harness.ix.answer_next({"name": "s1"})
    harness.shell.sessions.saveSession()
    path = harness.home / ".sirat" / "sessions" / "s1.json"
    created = json.loads(path.read_text())["created"]
    harness.ix.answer_next({"name": "s1"})
    harness.ix.answer_next(True)  # replace
    harness.shell.sessions.saveSession()
    assert harness.ix.confirms[-1].title == "Replace session s1?"
    assert json.loads(path.read_text())["created"] == created


@pytest.mark.req("34.load")
def test_load_session_restores_notes_formulas_actions_favorites_and_history(harness):
    make_history(harness)
    harness.ix.answer_next({"name": "before"})
    harness.shell.sessions.saveSession()

    harness.services.favorites.remove("MODEM.CTRL")
    harness.services.actions.remove("lpmode_on")
    harness.services.annotations.set_note("BUFC.LPMODE.LPENBYM33", "")
    harness.services.annotations.set_formula("SYNTH.FREQ.FREQ", "", "")
    harness.shell.history.clear()

    sessions = harness.shell.sessions
    sessions.openBrowser()
    sessions.select(0)
    harness.ix.answer_next(True)
    sessions.loadSelected()
    assert sessions.browserOpen is False
    assert "MODEM.CTRL" in harness.services.favorites.names
    assert "lpmode_on" in harness.services.actions.actions
    assert harness.services.annotations.note("BUFC.LPMODE.LPENBYM33") == "Set by sequencer on boot"
    assert harness.services.annotations.formula("SYNTH.FREQ.FREQ") == ("x / 1000", "MHz")
    assert [r["operation"] for r in harness.shell.history.model.items] == ["WRITE", "READ"]
    # written back to the normal settings files, so it survives a restart
    assert "MODEM.CTRL" in harness.restart().services.favorites.names


def test_load_asks_first_and_can_be_declined(harness):
    harness.ix.answer_next({"name": "s"})
    harness.shell.sessions.saveSession()
    harness.services.favorites.remove("MODEM.CTRL")
    harness.shell.sessions.select(0)
    harness.ix.answer_next(False)
    harness.shell.sessions.loadSelected()
    assert "MODEM.CTRL" not in harness.services.favorites.names


@pytest.mark.req("34.browse")
def test_browser_lists_newest_first_previews_and_deletes(harness):
    for name in ("first", "second"):
        harness.ix.answer_next({"name": name})
        harness.shell.sessions.saveSession()
    sessions = harness.shell.sessions
    assert set(session_names(harness)) == {"first", "second"}
    sessions.select(session_names(harness).index("first"))
    preview = {r["key"]: r["value"] for r in sessions.preview}
    assert preview["Name"] == "first" and preview["Actions"].startswith("4: lpmode_on")
    harness.ix.answer_next(True)
    sessions.deleteSelected()
    assert session_names(harness) == ["second"]
    assert not (harness.home / ".sirat" / "sessions" / "first.json").exists()


def test_names_with_odd_characters_are_saved_safely(harness):
    harness.ix.answer_next({"name": "rx/tx: 2026?"})
    harness.shell.sessions.saveSession()
    assert session_names(harness) == ["rx/tx: 2026?"]
    assert (harness.home / ".sirat" / "sessions" / "rx_tx_ 2026_.json").exists()


@pytest.mark.req("34.autosave")
def test_autosave_runs_every_5_minutes(harness):
    make_history(harness)
    autosave = harness.home / ".sirat" / "autosave.json"
    assert not autosave.exists()
    harness.scheduler.advance(5 * 60 * 1000)
    data = json.loads(autosave.read_text())
    assert data["session_name"] == "autosave" and len(data["history"]) == 2
    assert harness.shell.sessions.autosaveText.startswith("Auto-saved at ")


@pytest.mark.req("34.restore")
def test_history_comes_back_on_the_next_launch(qapp, tmp_path):
    first = Harness(tmp_path)
    make_history(first)
    first.container.stop()  # closing the app auto-saves once more
    second = Harness(tmp_path, seed=False)
    assert [e.target for e in second.services.history.entries] == ["BUFC.LPMODE", "BUFC.LPMODE"]
    assert any("Restored 2 history entries" in line.text for line in second.services.log.lines)


def test_a_broken_autosave_file_is_ignored(qapp, tmp_path):
    (tmp_path / ".sirat").mkdir(parents=True)
    (tmp_path / ".sirat" / "autosave.json").write_text("{ not json")
    h = Harness(tmp_path)
    assert h.services.history.entries == []
