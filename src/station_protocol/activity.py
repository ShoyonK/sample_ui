"""activity: aborting a running activity; and the activity.progress and activity.finished events.

An activity is long-running work a call starts (automation.seq.run, tests.run, a chamber wait, an ECA capture):
the call answers {activity_id} at once, progress comes as events, and activity.finished comes exactly once.
"""

from __future__ import annotations

from typing import Any, Dict, List

from typing_extensions import NotRequired, TypedDict

from station_protocol.errors import ApiError
from station_protocol.method import Event, Method, Param


class ActivityProgressData(TypedDict):
    activity_id: str
    pos: NotRequired[int]                  # a position's activity
    instrument_id: NotRequired[str]        # an instrument's activity (chamber wait, ECA capture)
    step: int
    total: int
    message: str
    group: NotRequired[str]                # automation.seq.run: the action the op came from; tests.run: test id
    result: NotRequired[Dict[str, Any]]    # tests.run: the test that just finished (StationTestResult)


class ActivityFinishedData(TypedDict):
    activity_id: str
    pos: NotRequired[int]
    instrument_id: NotRequired[str]
    ok: bool
    results: List[Dict[str, Any]]          # per op (seq.run) or per test (tests.run)
    error: NotRequired[ApiError]           # what ended it, as an error object
    result: NotRequired[Any]               # kind-specific, e.g. {capture_id} for instruments.eca.capture


METHODS = (
    Method("activity.abort", (Param("activity_id", str),), None),
)

PROGRESS = Event("activity.progress", ActivityProgressData, "activity")
FINISHED = Event("activity.finished", ActivityFinishedData, "activity")
