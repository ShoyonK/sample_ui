"""Ctrl+K command palette."""

import pytest


def results(h):
    return [(r["kind"], r["title"]) for r in h.shell.palette.results.items]


@pytest.fixture
def palette(harness):
    harness.shell.palette.open()
    return harness.shell.palette


def test_empty_query_offers_commands_and_pages(harness, palette):
    kinds = {k for k, _ in results(harness)}
    assert kinds == {"command", "page"}
    assert ("page", "Watch and logger") in results(harness)


@pytest.mark.req("plan.palette")
def test_register_matches_rank_exact_then_prefix_then_contains(harness, palette):
    palette.setQuery("bufc.lpmode")
    assert results(harness)[0] == ("register", "BUFC.LPMODE")
    palette.setQuery("lpmode")
    titles = [t for _, t in results(harness)]
    assert "BUFC.LPMODE" in titles and "BUFC_NS.LPMODE" not in titles  # _NS/_S follow the tree's filter


def test_field_names_find_their_register(harness, palette):
    palette.setQuery("opmode")
    row = next(r for r in harness.shell.palette.results.items if r["title"] == "MODEM.CTRL")
    assert row["subtitle"].startswith("field OPMODE")


def test_choosing_a_register_opens_and_reads_it(harness, palette):
    palette.setQuery("synth.freq")
    palette.activateCurrent()
    assert palette.isOpen is False
    assert harness.shell.currentPage == "registers"
    assert harness.shell.detail.title == "SYNTH.FREQ" and harness.shell.detail.hasValue


def test_choosing_a_page_action_and_sequence(harness, palette):
    palette.setQuery("sequences")
    palette.activateCurrent()
    assert harness.shell.currentPage == "sequences"

    palette.open()
    palette.setQuery("siggen")
    assert results(harness)[0] == ("action", "siggen_2440_0dbm")
    palette.activateCurrent()
    assert harness.shell.currentPage == "actions" and harness.shell.actions.currentName == "siggen_2440_0dbm"

    palette.open()
    palette.setQuery("lp_mode")
    palette.activate([t for _, t in results(harness)].index("lp_mode_check"))
    assert harness.shell.sequences.selectedName == "lp_mode_check"


def test_commands_run(harness, palette):
    palette.setQuery("dark")
    palette.activateCurrent()
    assert harness.shell.state.darkMode is True
    palette.open()
    palette.setQuery("connect to")
    palette.activateCurrent()
    assert harness.shell.connection.sheetOpen


def test_arrow_keys_move_and_wrap(harness, palette):
    palette.setQuery("bufc.buf0")
    count = harness.shell.palette.results.count
    assert count > 2
    palette.move(1)
    assert palette.currentIndex == 1
    palette.move(-2)
    assert palette.currentIndex == count - 1


def test_no_matches(harness, palette):
    palette.setQuery("zzzz-nothing")
    assert harness.shell.palette.results.count == 0
    palette.activateCurrent()  # nothing to do, no error


def test_register_name_after_the_dot_outranks_other_kinds(harness, palette):
    palette.setQuery("lpmode")  # also the start of the action "lpmode_on"
    assert results(harness)[0] == ("register", "BUFC.LPMODE")
