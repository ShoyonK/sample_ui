import pytest

from sirat_ui.core.search import search
from sirat_ui.gateway.fake.chip import build_chip

CHIP = build_chip()


@pytest.mark.req("6.empty-search")
def test_empty_search_shows_all_peripherals_collapsed_without_secure_variants():
    result = search(CHIP, "", show_secure=False)
    assert "BUFC" in result.peripherals
    assert not any(n.endswith(("_NS", "_S")) for n in result.peripherals)
    assert result.expanded == set()
    assert result.auto_select is None


def test_secure_variants_appear_when_enabled():
    assert "BUFC_NS" in search(CHIP, "", show_secure=True).peripherals


@pytest.mark.req("6.match-peripheral")
def test_matching_a_peripheral_shows_all_its_registers_expanded():
    result = search(CHIP, "bufc", show_secure=False)
    assert result.peripherals == ["BUFC"]
    assert result.registers["BUFC"] is None
    assert "BUFC" in result.expanded


@pytest.mark.req("6.match-register")
def test_matching_a_single_register_auto_selects_it():
    result = search(CHIP, "lpmode", show_secure=False)
    assert result.registers == {"BUFC": ["LPMODE"]}
    assert result.auto_select == "BUFC.LPMODE"


@pytest.mark.req("6.match-field")
def test_matching_a_field_shows_the_register_that_contains_it():
    result = search(CHIP, "lpenbyseq", show_secure=False)
    assert result.registers == {"BUFC": ["LPMODE"]}


def test_search_is_case_insensitive_and_multiple_matches_do_not_auto_select():
    result = search(CHIP, "STATUS", show_secure=False)
    assert len(result.peripherals) > 1
    assert result.auto_select is None
