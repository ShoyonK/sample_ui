"""WiFi PHY configuration (req 23): which options each standard allows, the PHY name, the config dict,
and the packet structure the live visualizer draws.

Assumptions where req 23 doesn't say: MP power mode only for 802.11ax/be ("HP|LP|MP or HP|LP"), rates in
Mb/s for b/g/a and MCS indexes for n/ac/ax/be, and bandwidths up to 40 MHz on 2.4 GHz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

Mode = Literal["RX", "TX"]

STANDARDS = ["802.11b", "802.11g", "802.11a", "802.11n", "802.11ac", "802.11ax", "802.11be"]
CHANNELS_2G = list(range(1, 12))
CHANNELS_5G = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144,
               149, 153, 157, 161, 165]
_BANDS = {"802.11b": "2g", "802.11g": "2g", "802.11a": "5g", "802.11ac": "5g",
          "802.11n": "both", "802.11ax": "both", "802.11be": "both"}
_LEGACY_RATES = {"802.11b": ["1", "2", "5.5", "11"],
                 "802.11g": ["6", "9", "12", "18", "24", "36", "48", "54"],
                 "802.11a": ["6", "9", "12", "18", "24", "36", "48", "54"]}
_MCS_COUNT = {"802.11n": 8, "802.11ac": 10, "802.11ax": 12, "802.11be": 14}
# Mb/s for one spatial stream at 20 MHz (n/ac 0.8 us GI, ax/be 0.8 us GI), for the airtime estimate
_MCS_RATE = [6.5, 13, 19.5, 26, 39, 52, 58.5, 65, 78, 86.7]
_HE_RATE = [8.6, 17.2, 25.8, 34.4, 51.6, 68.8, 77.4, 86.0, 103.2, 114.7, 129.0, 143.4, 154.9, 172.1]
TRANSMIT_MODES = ["BURST", "CONTINUES", "STREAM"]
PPDU_TYPES = {"802.11ax": ["HE_SU_PPDU", "HE_ER_SU_PPDU", "HE_MU_PPDU", "HE_TB_PPDU"],
              "802.11be": ["EHT_MU_PPDU", "EHT_TB_PPDU"]}
GI_LTF = ["1xLTF_0p8usGI", "2xLTF_0p8usGI", "2xLTF_1p6usGI", "4xLTF_0p8usGI", "4xLTF_3p2usGI"]
_BW_FACTOR = {"BW_20MHz": 1, "BW_40MHz": 2, "BW_80MHz": 4, "BW_160MHz": 8}
MAX_PKT_LENGTH, MAX_NUM_PKTS = 65535, 1_000_000


def is_advanced(standard: str) -> bool:
    return standard in ("802.11ax", "802.11be")


def channels(standard: str) -> List[int]:
    band = _BANDS[standard]
    return CHANNELS_2G if band == "2g" else CHANNELS_5G if band == "5g" else CHANNELS_2G + CHANNELS_5G


def power_modes(standard: str) -> List[str]:
    return ["HP", "LP", "MP"] if is_advanced(standard) else ["HP", "LP"]


def rates(standard: str) -> List[str]:
    """What the Rate/MCS drop-down shows. Rates are Mb/s; MCS entries are "MCS<n>"."""
    return _LEGACY_RATES.get(standard) or [f"MCS{i}" for i in range(_MCS_COUNT[standard])]


def default_rate(standard: str) -> str:
    return {"802.11b": "11", "802.11g": "24", "802.11a": "24"}.get(standard, "MCS7")


def bandwidths(channel: int) -> List[str]:
    return ["BW_20MHz", "BW_40MHz"] if channel in CHANNELS_2G else list(_BW_FACTOR)


def phy_name(standard: str, channel: int, power_mode: str) -> str:
    """Req 23: WIFI_2p4G or WIFI_5G; 802.11ax/be add the power mode, e.g. PHY_WIFI_2p4G_HP."""
    base = "WIFI_2p4G" if channel in CHANNELS_2G else "WIFI_5G"
    return f"PHY_{base}_{power_mode}" if is_advanced(standard) else base


@dataclass(frozen=True)
class WifiTxParams:
    pkt_length: int
    num_pkts: int
    transmit_mode: str
    aggr_enable: bool


@dataclass(frozen=True)
class WifiAdvanced:
    ppdu_type: str
    gi_ltf: str
    dcm: bool
    bandwidth: str


@dataclass(frozen=True)
class WifiPhyConfig:
    """What load_wifi_phy gets (req 23 "WiFi Config Structure"). to_dict() is the wire and action format."""
    mode: Mode
    standard: str
    channel: int
    power_mode: str
    rate: str  # Mb/s for b/g/a, MCS index for n/ac/ax/be
    phy_name: str
    tx_params: Optional[WifiTxParams] = None
    advanced: Optional[WifiAdvanced] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"mode": self.mode, "standard": self.standard, "channel": self.channel,
                               "power_mode": self.power_mode, "rate": self.rate, "phy_name": self.phy_name}
        if self.tx_params:
            out["tx_params"] = {"pkt_length": self.tx_params.pkt_length, "num_pkts": self.tx_params.num_pkts,
                                "transmit_mode": self.tx_params.transmit_mode,
                                "aggr_enable": self.tx_params.aggr_enable}
        if self.advanced:
            out["advanced"] = {"ppdu_type": self.advanced.ppdu_type, "gi_ltf": self.advanced.gi_ltf,
                               "dcm": int(self.advanced.dcm), "bandwidth": self.advanced.bandwidth}
        return out

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WifiPhyConfig":
        """Raises KeyError/ValueError/TypeError for a malformed dict (e.g. a hand-edited action)."""
        mode = str(data["mode"])
        if mode not in ("RX", "TX"):
            raise ValueError(f"mode must be RX or TX, not {mode}")
        tx = data.get("tx_params")
        adv = data.get("advanced")
        return WifiPhyConfig(
            "RX" if mode == "RX" else "TX", str(data["standard"]), int(data["channel"]), str(data["power_mode"]),
            str(data["rate"]), str(data["phy_name"]),
            WifiTxParams(int(tx["pkt_length"]), int(tx["num_pkts"]), str(tx["transmit_mode"]),
                         bool(tx["aggr_enable"])) if tx else None,
            WifiAdvanced(str(adv["ppdu_type"]), str(adv["gi_ltf"]), bool(adv["dcm"]),
                         str(adv["bandwidth"])) if adv else None)


@dataclass
class WifiSettings:
    """The WiFi PHY form's current choices. normalized() keeps them valid; config() builds what's sent."""
    mode: Mode = "RX"
    standard: str = "802.11g"
    channel: int = 6
    power_mode: str = "HP"
    rate: str = "24"
    pkt_length: int = 1500
    num_pkts: int = 0
    transmit_mode: str = "BURST"
    aggr_enable: bool = True
    advanced_enabled: bool = False
    ppdu_type: str = "HE_SU_PPDU"
    gi_ltf: str = "1xLTF_0p8usGI"
    dcm: bool = False
    bandwidth: str = "BW_20MHz"

    def normalized(self) -> "WifiSettings":
        """Keeps every choice valid for the current standard and channel (e.g. after changing standard)."""
        s = WifiSettings(**self.__dict__)
        if s.channel not in channels(s.standard):
            s.channel = 6 if 6 in channels(s.standard) else channels(s.standard)[0]
        if s.power_mode not in power_modes(s.standard):
            s.power_mode = "HP"
        if s.rate not in rates(s.standard):
            s.rate = default_rate(s.standard)
        if is_advanced(s.standard):
            if s.ppdu_type not in PPDU_TYPES[s.standard]:
                s.ppdu_type = PPDU_TYPES[s.standard][0]
            if s.bandwidth not in bandwidths(s.channel):
                s.bandwidth = "BW_20MHz"
        else:
            s.advanced_enabled = False
        return s

    def problems(self) -> List[str]:
        out = []
        if not 1 <= self.pkt_length <= MAX_PKT_LENGTH:
            out.append(f"Packet length must be 1 to {MAX_PKT_LENGTH} bytes")
        if not 0 <= self.num_pkts <= MAX_NUM_PKTS:
            out.append(f"Number of packets must be 0 to {MAX_NUM_PKTS}")
        return out

    def config(self) -> WifiPhyConfig:
        rate = self.rate[3:] if self.rate.startswith("MCS") else self.rate
        tx = WifiTxParams(self.pkt_length, self.num_pkts, self.transmit_mode, self.aggr_enable)             if self.mode == "TX" else None
        advanced = WifiAdvanced(self.ppdu_type, self.gi_ltf, self.dcm, self.bandwidth)             if is_advanced(self.standard) and self.advanced_enabled else None
        return WifiPhyConfig(self.mode, self.standard, self.channel, self.power_mode, rate,
                             phy_name(self.standard, self.channel, self.power_mode), tx, advanced)


# ---- packet visualizer --------------------------------------------------------------------------

@dataclass(frozen=True)
class Segment:
    name: str
    us: Optional[float]   # duration; None for the data part when it isn't known (RX)
    kind: str             # legacy | standard | data | pad


@dataclass
class PacketLayout:
    segments: List[Segment] = field(default_factory=list)
    caption: str = ""


_L = [Segment("L-STF", 8, "legacy"), Segment("L-LTF", 8, "legacy"), Segment("L-SIG", 4, "legacy")]
_PREAMBLES = {
    "802.11b": [Segment("Preamble", 144, "legacy"), Segment("PLCP header", 48, "legacy")],
    "802.11g": _L, "802.11a": _L,
    "802.11n": _L + [Segment("HT-SIG", 8, "standard"), Segment("HT-STF", 4, "standard"),
                     Segment("HT-LTF", 4, "standard")],
    "802.11ac": _L + [Segment("VHT-SIG-A", 8, "standard"), Segment("VHT-STF", 4, "standard"),
                      Segment("VHT-LTF", 4, "standard"), Segment("VHT-SIG-B", 4, "standard")],
    "802.11ax": _L + [Segment("RL-SIG", 4, "standard"), Segment("HE-SIG-A", 8, "standard"),
                      Segment("HE-STF", 4, "standard"), Segment("HE-LTF", 8, "standard")],
    "802.11be": _L + [Segment("RL-SIG", 4, "standard"), Segment("U-SIG", 8, "standard"),
                      Segment("EHT-SIG", 4, "standard"), Segment("EHT-STF", 4, "standard"),
                      Segment("EHT-LTF", 8, "standard")],
}


def data_rate_mbps(settings: WifiSettings) -> float:
    if settings.rate in _LEGACY_RATES.get(settings.standard, []):
        return float(settings.rate)
    mcs = int(settings.rate[3:])
    table = _HE_RATE if is_advanced(settings.standard) else _MCS_RATE
    factor = _BW_FACTOR.get(settings.bandwidth, 1) if is_advanced(settings.standard) and settings.advanced_enabled else 1
    return table[min(mcs, len(table) - 1)] * factor


def packet_layout(settings: WifiSettings) -> PacketLayout:
    s = settings.normalized()
    preamble = list(_PREAMBLES[s.standard])
    rate = data_rate_mbps(s)
    preamble_us = sum(seg.us or 0 for seg in preamble)
    if s.mode == "TX":
        data_us = round(s.pkt_length * 8 / rate, 1)
        data = Segment(f"Data · {s.pkt_length} B", data_us, "data")
        caption = (f"Preamble {preamble_us:g} µs · data about {data_us:g} µs at {rate:g} Mb/s · "
                   f"{'continuous' if s.num_pkts == 0 else f'{s.num_pkts} packets'}, {s.transmit_mode}")
    else:
        data = Segment("Data", None, "data")
        caption = f"Receiving {s.standard} on channel {s.channel} · preamble {preamble_us:g} µs · up to {rate:g} Mb/s"
    tail = [Segment("PE", 4, "pad")] if is_advanced(s.standard) else []
    return PacketLayout(preamble + [data] + tail, caption)
