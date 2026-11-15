"""tests: the tests a station can run, and running them as one activity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from station_protocol.common import ACTIVITY, POS
from station_protocol.method import Method, Param


@dataclass
class StationTest:
    """One test the station can run (tests.list)."""
    id: str
    name: str


METHODS = (
    Method("tests.list", (), List[StationTest], wrap="tests"),
    Method("tests.run", (POS, Param("test_ids", List[str])), str, wrap=ACTIVITY, requires=("dut", "idle", "no_fault")),
)
