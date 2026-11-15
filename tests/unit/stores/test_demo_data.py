"""The demo data the fake backend starts with (stores/demo_data.py)."""

import datetime as dt

from sibench_ui.core.dumps import compare, read_csv
from sibench_ui.gateway.fake.chip import build_chip
from sibench_ui.stores.demo_data import DEMO_WATCH, seed_demo_dumps

DAY = dt.date(2026, 11, 14)


def _lookup():
    registers = {r.full_name: r for p in build_chip() for r in p.registers}
    return registers.get


def test_three_demo_dumps_are_written_into_an_empty_folder_only(tmp_path):
    written = seed_demo_dumps(tmp_path, build_chip(), DAY)
    assert [read_csv(p).name for p in written] == ["after_boot", "ble_1m_rx", "ble_1m_rx_40C"]
    assert all(read_csv(p).timestamp.date() == DAY for p in written)
    assert seed_demo_dumps(tmp_path, build_chip(), DAY) == []   # never on top of dumps already there


def test_neighbouring_demo_dumps_differ_in_a_few_registers_with_field_detail(tmp_path):
    boot, rx, hot = (read_csv(p) for p in seed_demo_dumps(tmp_path, build_chip(), DAY))
    setup = compare(boot.values, rx.values, _lookup(), title="", before_label="", after_label="")
    assert 8 <= len(setup.rows) <= 16 < setup.compared   # a clear diff: most registers are the same
    changes = {row.register: row.change for row in setup.rows}
    assert changes["MODEM.CTRL"] == "OPMODE 0→2, CODING 0→1, DEMODSEL 0→2"
    assert "RADIOAES 0→1" in changes["CMU.CLKEN0"]
    warm = compare(rx.values, hot.values, _lookup(), title="", before_label="", after_label="")
    assert {row.register for row in warm.rows} == {"AGC.CTRL0", "AGC.RSSI", "SYNTH.FREQ"}


def test_every_watched_demo_field_exists_on_the_fake_chip():
    fields = {f.full_name for p in build_chip() for r in p.registers for f in r.fields}
    assert [name for name in DEMO_WATCH if name not in fields] == []
