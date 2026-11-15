"""Switching DUT loads that DUT's register tree: each DUT can be a different chip (app/container.py
_position_changed, ConnectionService.show_position, RegisterCatalog.load)."""

from sibench_ui.gateway.fake.chip import build_chip


def names(harness):
    return [p.name for p in harness.services.catalog.peripherals]


def second_dut(harness, peripherals=("AGC", "MODEM")):
    """DUT 2 is a smaller chip, connected through the connect sheet's path (select it, then connect)."""
    harness.fake.replace_dut(2, peripherals=[p for p in build_chip() if p.name in peripherals])
    harness.state.set_position(2)
    harness.services.connection.connect(2)
    harness.scheduler.run_pending()


def test_switching_dut_shows_the_new_dut_tree_and_back(harness):
    full = names(harness)
    second_dut(harness)
    assert names(harness) == ["AGC", "MODEM"]
    assert harness.services.catalog.register("BUFC.LPMODE") is None
    harness.state.set_position(1)
    harness.scheduler.run_pending()
    assert names(harness) == full


def test_switching_to_a_position_with_no_dut_empties_the_tree(harness):
    harness.state.set_position(3)
    harness.scheduler.run_pending()
    assert names(harness) == []


def test_a_tree_that_arrives_after_you_switched_again_is_dropped(harness):
    second_dut(harness)
    harness.fake.auto_resolve = False
    harness.state.set_position(1)          # DUT 1's tree is on its way
    harness.state.set_position(3)          # nothing at 3: empty now
    harness.fake.release()
    harness.scheduler.run_pending()
    assert names(harness) == []


def test_disconnecting_a_dut_that_is_not_selected_keeps_the_tree(harness):
    full = names(harness)
    harness.services.connection.connect(2)  # DUT 2 connects while DUT 1 stays on screen
    harness.scheduler.run_pending()
    assert names(harness) == full
    harness.services.connection.disconnect(2)
    harness.scheduler.run_pending()
    assert names(harness) == full
