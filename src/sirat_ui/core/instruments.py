"""Instrument settings, validation and generated code (req 25 signal generator, 26 BLE packet, 27 GFSK packet).

Pure functions: the services and ViewModels in domains/instruments use them, and the tests check them directly.
The generated scripts import from `packet_generator`, the station's packet generator library.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sirat_ui.models.instruments import BlePacket, GfskPacket, SiggenSettings

# ---- signal generator (req 25) -----------------------------------------------------------------------------

FREQ_RANGE_MHZ = (0.001, 6000.0)
POWER_RANGE_DBM = (-150.0, 30.0)


def _number(text: str) -> Optional[float]:
    try:
        return float(text.strip())
    except ValueError:
        return None


def parse_overrides(text: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """'KEY=value, KEY2=3' -> ({KEY: "value", KEY2: 3}, None), or ({}, problem). Numbers stay numbers."""
    out: Dict[str, Any] = {}
    for part in [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]:
        key, sep, value = part.partition("=")
        if not sep or not key.strip():
            return {}, f"'{part}' isn't KEY=value"
        value = value.strip()
        number = _number(value)
        out[key.strip()] = (int(number) if number is not None and number.is_integer() and "." not in value
                            else number if number is not None else value)
    return out, None


def format_overrides(overrides: Dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in overrides.items())


def siggen_problems(sg_type: str, frequency: str, power: str, overrides: str) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    if not sg_type.strip():
        errors["sgType"] = "Type can't be empty"
    freq = _number(frequency)
    lo, hi = FREQ_RANGE_MHZ
    if freq is None or not lo <= freq <= hi:
        errors["frequency"] = f"Frequency must be between {lo:g} and {hi:g} MHz"
    pwr = _number(power)
    plo, phi = POWER_RANGE_DBM
    if pwr is None or not plo <= pwr <= phi:
        errors["power"] = f"Power must be between {plo:g} and {phi:g} dBm"
    if parse_overrides(overrides)[1]:
        errors["overrides"] = "Use KEY=value, separated by commas"
    return errors


def siggen_code(s: SiggenSettings, instrument_id: str = "siggen1") -> str:
    """Req 25 "Includes generated code for reproduction"."""
    return "\n".join([
        f"sg_role = dut.instruments['{instrument_id}']  # the bench's signal generator role",
        "config = {",
        f"    'Type': {s.sg_type!r},",
        f"    'InputConfigName': {s.input_config_name!r},",
        f"    'Frequency': {s.frequency_mhz * 1e6:.0f},  # Hz ({s.frequency_mhz:g} MHz)",
        f"    'OutputPower': {s.power_dbm:g},  # dBm",
        f"    'Overrides': {dict(s.overrides)!r},",
        "}",
        "sg_role.LoadConfig(config)",
    ])


def siggen_op(s: SiggenSettings, instrument_id: str) -> Dict[str, Any]:
    """Req 25 "Action Format", plus the instrument it was made for (core/wire_ops.py sends that)."""
    return {"type": "signal_generator", **s.to_json(), "instrument_id": instrument_id,
            "code": siggen_code(s, instrument_id)}


def siggen_action_name(s: SiggenSettings) -> str:
    power = f"{s.power_dbm:g}".replace("-", "m").replace(".", "p")
    return f"siggen_{s.frequency_mhz:g}_{power}dbm".replace(".", "p")


# ---- BLE packet (req 26) -----------------------------------------------------------------------------------

BLE_DEFAULTS = {"access_address": "0x8E89BED6", "crc_init": "0x555555", "whitening_init": 37, "preamble": "0xAA"}


def _hex(text: str, bits: int) -> Optional[int]:
    t = text.strip().lower()
    t = t[2:] if t.startswith("0x") else t
    if not t or any(c not in "0123456789abcdef" for c in t):
        return None
    value = int(t, 16)
    return value if value < (1 << bits) else None


def ble_problems(access_address: str, crc_init: str, whitening: str, preamble: str) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    if _hex(access_address, 32) is None:
        errors["accessAddress"] = "A 32-bit hex value, like 0x8E89BED6"
    if _hex(crc_init, 24) is None:
        errors["crcInit"] = "A 24-bit hex value, like 0x555555"
    try:
        if not 0 <= int(whitening.strip()) <= 127:
            raise ValueError
    except ValueError:
        errors["whitening"] = "A whole number from 0 to 127"
    if _hex(preamble, 8) is None:
        errors["preamble"] = "An 8-bit hex value, like 0xAA"
    return errors


def parse_ble(access_address: str, crc_init: str, whitening: str, preamble: str) -> Optional[BlePacket]:
    if ble_problems(access_address, crc_init, whitening, preamble):
        return None
    aa, crc, pre = _hex(access_address, 32), _hex(crc_init, 24), _hex(preamble, 8)
    assert aa is not None and crc is not None and pre is not None
    return BlePacket(aa, crc, int(whitening.strip()), pre)


def ble_from_json(data: Dict[str, Any]) -> BlePacket:
    packet = parse_ble(str(data.get("access_address", BLE_DEFAULTS["access_address"])),
                       str(data.get("crc_init", BLE_DEFAULTS["crc_init"])),
                       str(data.get("whitening_init", BLE_DEFAULTS["whitening_init"])),
                       str(data.get("preamble", BLE_DEFAULTS["preamble"])))
    return packet or BlePacket()


def ble_code(p: BlePacket) -> str:
    """Req 26 "Code Generation": builds the BLE packet structure for the signal generator."""
    return "\n".join([
        "# BLE packet configuration (generated by SiRAT)",
        "from packet_generator.ble import BleLinkLayerPacket",
        "",
        "packet = BleLinkLayerPacket(",
        f"    preamble=0x{p.preamble:02X},",
        f"    access_address=0x{p.access_address:08X},",
        f"    sync_word=0x{p.sync_word:08X},  # access address in on-air bit order",
        f"    crc_init=0x{p.crc_init:06X},",
        f"    whitening_init={p.whitening_init},  # channel index seed",
        ")",
        "bits = packet.build()",
    ])


# ---- GFSK packet (req 27) ----------------------------------------------------------------------------------

PAYLOADS = ["PRBS9", "0x00", "0xFF", "0x55"]


def gfsk_problems(rate: str, deviation: str, bt: str, frequency: str, power: str, length: str) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    r, d, b = _number(rate), _number(deviation), _number(bt)
    if r is None or not 1 <= r <= 4000:
        errors["rate"] = "Symbol rate must be between 1 and 4000 kbps"
    if d is None or not 0 < d <= 2000:
        errors["deviation"] = "Deviation must be between 0 and 2000 kHz"
    if b is None or not 0.1 <= b <= 1.0:
        errors["bt"] = "BT must be between 0.1 and 1.0"
    errors.update({k: v for k, v in siggen_problems("x", frequency, power, "").items()})
    try:
        if not 1 <= int(length.strip()) <= 255:
            raise ValueError
    except ValueError:
        errors["length"] = "Payload length must be 1 to 255 bytes"
    return errors


def gfsk_code(g: GfskPacket, instrument_id: str = "siggen1") -> str:
    """Req 27: self-contained code that builds the packet and plays it on the signal generator."""
    payload = ("prbs9(length)" if g.payload == "PRBS9"
               else f"bytes([{g.payload}] * length)")
    return "\n".join([
        "# GFSK packet (generated by SiRAT)",
        "from packet_generator.gfsk import GfskModulator, prbs9",
        "",
        f"length = {g.payload_length}",
        f"payload = {payload}",
        "modulator = GfskModulator(",
        f"    symbol_rate_hz={g.symbol_rate_kbps * 1e3:.0f},",
        f"    deviation_hz={g.deviation_khz * 1e3:.0f},",
        f"    bt={g.bt:g},",
        ")",
        "iq = modulator.modulate(payload)",
        f"sg_role = dut.instruments['{instrument_id}']",
        f"sg_role.PlayIq(iq, frequency_hz={g.frequency_mhz * 1e6:.0f}, power_dbm={g.power_dbm:g})",
    ])


def gfsk_op(g: GfskPacket, instrument_id: str = "siggen1") -> Dict[str, Any]:
    """Req 27 "Action Format"."""
    return {"type": "gfsk_packet", "code": gfsk_code(g, instrument_id)}


__all__: List[str] = ["SiggenSettings", "BlePacket", "GfskPacket"]
