import pytest
from hypothesis import given
from hypothesis import strategies as st

from sirat_ui.core import bits
from sirat_ui.core.formatting import ValueFormat, format_value, parse_value


@given(value=st.integers(0, 2**32 - 1), lsb=st.integers(0, 31), data=st.data())
def test_insert_then_extract_returns_the_field_value(value, lsb, data):
    width = data.draw(st.integers(1, 32 - lsb))
    field_value = data.draw(st.integers(0, bits.mask(width)))
    assert bits.extract(bits.insert(value, lsb, width, field_value), lsb, width) == field_value


@given(value=st.integers(0, 2**32 - 1), lsb=st.integers(0, 28))
def test_insert_leaves_other_bits_untouched(value, lsb):
    result = bits.insert(value, lsb, 4, 0xA)
    outside = ~(0xF << lsb) & 0xFFFFFFFF
    assert result & outside == value & outside


def test_insert_rejects_values_wider_than_the_field():
    with pytest.raises(ValueError):
        bits.insert(0, 0, 2, 4)


@given(st.integers(0, 2**32 - 1))
def test_toggle_twice_is_identity(value):
    assert bits.toggle(bits.toggle(value, 7), 7) == value


@pytest.mark.parametrize("fmt", list(ValueFormat))
@given(value=st.integers(0, 2**32 - 1))
def test_format_then_parse_round_trips(fmt, value):
    assert parse_value(format_value(value, fmt), fmt) == value


@pytest.mark.parametrize("text, default, expected", [
    ("0x10", ValueFormat.DEC, 16),
    ("0b101", ValueFormat.HEX, 5),
    ("ff", ValueFormat.HEX, 255),
    ("10", ValueFormat.DEC, 10),
    ("0x0000_00FF", ValueFormat.HEX, 255),
])
def test_parse_value_understands_prefixes_and_the_selected_format(text, default, expected):
    assert parse_value(text, default) == expected


@pytest.mark.parametrize("text", ["", "  ", "-1", "0xZZ", "hello"])
def test_parse_value_rejects_bad_input_with_a_message(text):
    with pytest.raises(ValueError) as exc:
        parse_value(text)
    assert str(exc.value)
