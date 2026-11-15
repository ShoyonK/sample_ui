"""Types more than one group uses: parameter ranges, the station's facts, the chip, and an RPC address."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import Field
from typing_extensions import Annotated

from station_protocol.method import Param

# Parameter types with their ranges; a server checks them when it validates params.
Position = Annotated[int, Field(ge=1, le=4)]
Offset = Annotated[int, Field(ge=0)]
Count = Annotated[int, Field(ge=1)]

POS = Param("pos", Position)          # the DUT position a call acts on
ID = Param("id", str)                 # the instrument a call acts on
ACTIVITY = "activity_id"              # the wrap key of every call that starts an activity


@dataclass(frozen=True)
class Fault:
    """Why a position is faulted: a hardware error during an activity. sys.recover clears it."""
    cause: str     # the error's data.cause when the library said (rpc_timeout, rail_assert...), else its code
    detail: str    # the error message, shown to the user
    at: str        # when it happened, ISO 8601 UTC


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


@dataclass
class StationStatus:
    """sys.status: the release, every position's facts, the instruments, and who holds the station (if anyone)."""
    release_id: str
    positions: List[PositionFacts] = field(default_factory=list)
    instruments: List[InstrumentFacts] = field(default_factory=list)
    claim: Optional[str] = None


@dataclass(frozen=True)
class ChipInfo:
    """The connected chip: part, revision, family."""
    part: str
    revision: str
    family: str


@dataclass(frozen=True)
class RpcAddress:
    """Where a DUT's RPC server listens; None in calls means "the workspace config's address"."""
    host: str
    port: int
