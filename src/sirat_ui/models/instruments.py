"""Instrument types: signal generator settings, BLE and GFSK packets (req 25-27) and ECA captures (req 30)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sirat_ui.core.bits import bit_reverse
from sirat_ui.models.station import CaptureMeta


@dataclass
class SiggenSettings:
    """~/.sirat/signal_generator.json (req 25 "Persistence File"): MHz, as the file and the GUI use."""
    sg_type: str = "PacketSrw"
    input_config_name: str = "BLE_1M"
    frequency_mhz: float = 2440.0
    power_dbm: float = 0.0
    overrides: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {"sg_type": self.sg_type, "input_config_name": self.input_config_name,
                "frequency_mhz": self.frequency_mhz, "power_dbm": self.power_dbm, "overrides": dict(self.overrides)}

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "SiggenSettings":
        return cls(str(data.get("sg_type", "PacketSrw")), str(data.get("input_config_name", "")),
                   float(data.get("frequency_mhz", 2440.0)), float(data.get("power_dbm", 0.0)),
                   dict(data.get("overrides") or {}))


@dataclass(frozen=True)
class BlePacket:
    access_address: int = 0x8E89BED6
    crc_init: int = 0x555555
    whitening_init: int = 37
    preamble: int = 0xAA

    @property
    def sync_word(self) -> int:
        """The access address in on-air bit order (BLE sends it LSB first), as a sync-word detector sees it."""
        return bit_reverse(self.access_address, 32)

    def to_json(self) -> Dict[str, Any]:
        return {"access_address": f"0x{self.access_address:08X}", "crc_init": f"0x{self.crc_init:06X}",
                "whitening_init": self.whitening_init, "preamble": f"0x{self.preamble:02X}"}


@dataclass(frozen=True)
class GfskPacket:
    symbol_rate_kbps: float = 1000.0
    deviation_khz: float = 250.0
    bt: float = 0.5
    frequency_mhz: float = 2440.0
    power_dbm: float = 0.0
    payload: str = "PRBS9"
    payload_length: int = 37


@dataclass
class Capture:
    meta: CaptureMeta
    channels: Dict[str, List[int]]

    @property
    def rate(self) -> float:
        return self.meta.spec.sample_rate_hz

    @property
    def trigger_ms(self) -> float:
        """Where the trigger is, in ms from the start of the capture."""
        spec = self.meta.spec
        return spec.duration_s * spec.pretrigger_pct / 100 * 1e3

    def time_ms(self, index: int) -> float:
        return index / self.rate * 1e3


@dataclass(frozen=True)
class Measurement:
    channel: str
    minimum: int
    maximum: int
    mean: float
    rising_edges: int
    frequency_hz: Optional[float]      # from the spacing of rising edges
    high_time_us: Optional[float]      # mean pulse width
    first_rise_ms: Optional[float]
