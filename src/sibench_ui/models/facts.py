"""What the station says about each DUT position and each instrument (docs/API_DESIGN.md "Facts")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Fault:
    """Why a position is faulted: a hardware error during an activity. sys.recover clears it."""
    cause: str     # the error's data.cause when the library said (rpc_timeout, rail_assert...), else its code
    detail: str    # the error message, shown to the user
    at: str        # when it happened, ISO 8601 UTC

    def __str__(self) -> str:
        return self.detail or self.cause


@dataclass
class PositionFacts:
    """One DUT position as sys.status reports it. activity: idle | executing ...; fault: set by a hardware error
    during a run, cleared by sys.recover."""
    position: int
    dut_connected: bool = False
    phy: Optional[str] = None
    watching: bool = False
    rf_path: Optional[str] = None       # rf.connect
    activity: str = "idle"
    fault: Optional[Fault] = None


@dataclass
class InstrumentFacts:
    """One bench instrument as sys.status reports it. activity is the instrument's own (waiting, capturing)."""
    id: str                             # "siggen1", "switch1", "chamber1", "eca1"
    kind: str                           # signal_generator | rf_switch | chamber | eca
    connected: bool = False
    model: str = ""
    activity: str = "idle"
