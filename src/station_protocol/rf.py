"""rf: the RF switch's paths, and PRS signal routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from station_protocol.common import POS
from station_protocol.method import Method, Param

RF_SWITCH = ("instrument:rf_switch",)


@dataclass(frozen=True)
class PrsRoute:
    """A PRS route: a signal to a pin over a channel."""
    signal: str
    pin: str
    channel: int


@dataclass(frozen=True)
class PrsSignalCatalog:
    """The PRS signals the chip family's module defines (sorted), and where they came from."""
    family: str
    module: str
    signals: Tuple[str, ...]


METHODS = (
    Method("rf.paths", (), List[str], wrap="names", requires=RF_SWITCH),
    Method("rf.connect", (POS, Param("path", str)), None, requires=RF_SWITCH),
    Method("rf.disconnect", (POS,), None, requires=RF_SWITCH),
    Method("rf.prs_route", (POS, Param("route", PrsRoute)), None, requires=("dut",)),
    Method("rf.prs_signals", (POS,), PrsSignalCatalog, requires=("dut",)),
)
