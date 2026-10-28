"""What the station says about each DUT position and each instrument (docs/API_DESIGN.md "Facts")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionFacts:
    position: int
    dut_connected: bool = False
    phy: Optional[str] = None
    watching: bool = False
    rf_path: Optional[str] = None       # rf.connect
    activity: str = "idle"
    fault: Optional[str] = None


@dataclass
class InstrumentFacts:
    id: str                             # "siggen1", "switch1", "chamber1", "eca1"
    kind: str                           # signal_generator | rf_switch | chamber | eca
    connected: bool = False
    model: str = ""
    activity: str = "idle"
