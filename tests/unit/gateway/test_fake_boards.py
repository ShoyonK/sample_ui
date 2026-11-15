"""Each position of the fake station is its own DUT (gateway/fake/board.py): registers never leak between them."""

from sibench_ui.gateway.fake import FakeStationGateway
from sibench_ui.gateway.fake.chip import build_chip
from sibench_ui.gateway.scheduler import ManualScheduler
from sibench_ui.models.registers import ChipInfo


def value(call):
    out = []
    call.then(out.append, lambda e: out.append(e.code))
    return out[0]


def two_duts() -> FakeStationGateway:
    fake = FakeStationGateway(ManualScheduler())
    fake.connect_dut(1)
    fake.connect_dut(2)
    return fake


def reset(fake, name):
    return fake.board(1).memory.get(name).reset


def test_a_write_on_one_dut_does_not_show_on_another():
    fake = two_duts()
    value(fake.write_register(1, "BUFC.LPMODE", 2))
    assert value(fake.read_register(1, "BUFC.LPMODE")) == 2
    assert value(fake.read_register(2, "BUFC.LPMODE")) == reset(fake, "BUFC.LPMODE") != 2
    value(fake.write_field(2, "MODEM.CTRL", "OPMODE", 2))
    assert value(fake.read_register(1, "MODEM.CTRL")) == reset(fake, "MODEM.CTRL")


def test_a_sequence_writes_only_its_own_dut():
    fake = two_duts()
    fake.run_sequence(2, [{"type": "register_write", "register": "AGC.CTRL0", "value": 0x013C}])
    fake.scheduler.run_pending()
    assert fake.board(2).memory.values["AGC.CTRL0"] == 0x013C != reset(fake, "AGC.CTRL0")
    assert fake.board(1).memory.values["AGC.CTRL0"] == reset(fake, "AGC.CTRL0")


def test_watch_ticks_move_only_the_watched_dut():
    fake = two_duts()
    before = dict(fake.board(2).memory.values)
    value(fake.watch(1, ["AGC.RSSI"], 0.5))
    fake.emit_watch_tick()
    assert fake.board(2).memory.values == before


def test_a_position_can_hold_another_chip_with_its_own_tree():
    fake = two_duts()
    tree = [p for p in build_chip() if p.name in ("AGC", "MODEM")]
    fake.replace_dut(2, ChipInfo("SIWG917M", "B0", "EVEREST"), tree)
    assert [p.name for p in value(fake.register_tree(2))] == ["AGC", "MODEM"]
    assert len(value(fake.register_tree(1))) > 2
    assert value(fake.connect_dut(2)).chip.family == "EVEREST"
    assert value(fake.connect_dut(1)).chip.family != "EVEREST"
    assert "<DUT 2: SIWG917M B0>" == repr(fake.advanced.dut(2))
