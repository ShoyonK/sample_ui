"""Pure instrument helpers: requires for instruments, BLE/GFSK/siggen code, ECA decoding and measurements."""

import base64
from array import array

from sirat_ui.core.bits import bit_reverse
from sirat_ui.core.eca import decimate, decode, format_ms, measure
from sirat_ui.core.instruments import parse_overrides, siggen_action_name, siggen_problems
from sirat_ui.core.requires import check_requires
from sirat_ui.models.facts import InstrumentFacts, PositionFacts
from sirat_ui.models.instruments import BlePacket, SiggenSettings


def test_instrument_idle_checks_the_instrument_not_the_position():
    busy_dut = PositionFacts(1, dut_connected=True, activity="executing")
    chamber = InstrumentFacts("chamber1", "chamber", True)
    assert check_requires("instruments.chamber.set_temp", busy_dut, [chamber], "chamber1") == []
    chamber.activity = "waiting"
    assert check_requires("instruments.chamber.set_temp", PositionFacts(1), [chamber], "chamber1") == ["idle"]


def test_an_instrument_id_must_name_a_connected_instrument():
    instruments = [InstrumentFacts("siggen1", "signal_generator", True),
                   InstrumentFacts("siggen2", "signal_generator", False)]
    assert check_requires("instruments.siggen.rf", None, instruments, "siggen1") == []
    assert check_requires("instruments.siggen.rf", None, instruments, "siggen2") == \
        ["instrument:signal_generator"]


def test_siggen_validation_overrides_and_names():
    assert siggen_problems("PacketSrw", "2440", "0", "") == {}
    assert set(siggen_problems("", "0", "31", "x")) == {"sgType", "frequency", "power", "overrides"}
    assert parse_overrides("GAIN=3, MODE=burst, TRIM=0.5") == ({"GAIN": 3, "MODE": "burst", "TRIM": 0.5}, None)
    assert siggen_action_name(SiggenSettings(frequency_mhz=2402.5, power_dbm=-10)) == "siggen_2402p5_m10dbm"


def test_ble_sync_word_is_the_access_address_in_on_air_order():
    assert bit_reverse(0b1011, 4) == 0b1101
    assert BlePacket().sync_word == 0x6B7D9171
    assert bit_reverse(BlePacket().sync_word, 32) == 0x8E89BED6


def test_decode_little_endian_int16():
    data = base64.b64encode(array("h", [0, -1, 3300]).tobytes()).decode()
    assert decode(data) == [0, -1, 3300]


def test_measure_a_square_wave():
    values = ([0] * 30 + [3300] * 10) * 5          # 1 MHz: 40 µs period, 10 µs high
    m = measure("PA_EN", values, 1e6)
    assert (m.rising_edges, round(m.frequency_hz), m.high_time_us, round(m.first_rise_ms, 6)) == (5, 25000, 10.0, 0.03)
    assert measure("flat", [5] * 10, 1e6).rising_edges == 0


def test_decimate_keeps_short_pulses():
    values = [0] * 100_000
    values[54_321] = 3300                          # one sample high
    xs, ys = decimate(values, 1e6, points=500)
    assert len(xs) <= 1000 and max(ys) == 3300
    xs, _ = decimate(values, 1e6, window=(10.0, 10.5))
    assert xs[0] == 10.0 and len(xs) == 502        # zoomed in: every sample


def test_format_ms_picks_the_unit():
    assert (format_ms(0.376), format_ms(1.25)) == ("376 µs", "1.25 ms")
