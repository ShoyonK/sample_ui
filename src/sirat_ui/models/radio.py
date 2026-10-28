"""Radio and PHY types: the WiFi PHY config and packet layout (req 23), Radio Calculator configs (req 21)
and PRS signals (req 24)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


Mode = Literal["RX", "TX"]


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


@dataclass(frozen=True)
class Segment:
    name: str
    us: Optional[float]   # duration; None for the data part when it isn't known (RX)
    kind: str             # legacy | standard | data | pad


@dataclass
class PacketLayout:
    segments: List[Segment] = field(default_factory=list)
    caption: str = ""


@dataclass(frozen=True)
class ConfigEntry:
    peripheral: str
    register: str
    field: str
    expected: int

    @property
    def register_name(self) -> str:
        return f"{self.peripheral}.{self.register}"

    @property
    def path(self) -> str:
        return f"{self.register_name}.{self.field}"


@dataclass
class RadioConfig:
    name: str
    entries: List[ConfigEntry] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)  # "line 7: ..." for lines that aren't assignments

    @property
    def field_counts(self) -> Dict[str, int]:
        """Fields per peripheral, in the order the peripherals first appear."""
        return dict(Counter(e.peripheral for e in self.entries))


@dataclass(frozen=True)
class Signal:
    name: str
    category: str = ""

    @property
    def label(self) -> str:
        return f"{self.name}  ({self.category})" if self.category else self.name
