"""tests.* for the fake station (req 33). Proposed API, not agreed with the backend yet (docs/API_DESIGN.md).

A test is one call to its execute(); what happens inside is hidden, so a test reports only pass or fail, a note
when it fails, and whatever it printed. A run is an activity: activity.progress as each test starts (group = the
test id) and again with `result` as it ends; activity.finished carries every result.

The tests below are placeholders so the page has something to run.
Test knobs (on station.station_tests): outcomes (test id -> True to pass, False to fail), runs.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.scheduler import Scheduler
from sirat_ui.models.facts import PositionFacts
from sirat_ui.models.station import ActivityFinished, ActivityProgress, StationTest

# id -> (name, run time in ms, passes, note when it fails, printed output)
_SAMPLES: Dict[str, Tuple[str, int, bool, str, List[str]]] = {
    "sample_test_1": ("Sample test 1", 600, True, "", ["sample_test_1: done"]),
    "sample_test_2": ("Sample test 2", 800, True, "", ["sample_test_2: done"]),
    "sample_test_3": ("Sample test 3", 700, False, "AssertionError: sample failure",
                      ["sample_test_3: started", "AssertionError: sample failure"]),
    "sample_test_4": ("Sample test 4", 900, True, "", ["sample_test_4: done"]),
}
CATALOGUE: List[StationTest] = [StationTest(test_id, sample[0]) for test_id, sample in _SAMPLES.items()]


class TestsHost(Protocol):
    facts: Dict[int, PositionFacts]
    clock: Callable[[], float]


@dataclass
class TestRunState:
    activity_id: str
    position: int
    test_ids: List[str]
    index: int = 0
    aborted: bool = False
    results: List[Dict[str, Any]] = field(default_factory=list)


class FakeStationTests:
    def __init__(self, respond: Callable[..., Call], host: TestsHost, scheduler: Scheduler,
                 emit: Callable[[Any], None], emit_status: Callable[[], None]) -> None:
        self._respond = respond
        self._host = host
        self._scheduler = scheduler
        self._emit = emit
        self._emit_status = emit_status
        self._ids = itertools.count(1)
        self.outcomes: Dict[str, bool] = {}
        self.runs: Dict[str, TestRunState] = {}

    def list_tests(self) -> Call[List[StationTest]]:
        return self._respond("tests.list", None, lambda: list(CATALOGUE))

    def run_tests(self, position: int, test_ids: List[str]) -> Call[str]:
        def run() -> str:
            unknown = [i for i in test_ids if i not in _SAMPLES]
            if not test_ids or unknown:
                raise ApiError(ErrorCode.INVALID_PARAMS, f"Unknown tests: {', '.join(unknown)}" if unknown
                               else "No tests to run")
            activity = TestRunState(f"t{next(self._ids)}", position, list(test_ids))
            self.runs[activity.activity_id] = activity
            self._host.facts[position].activity = "executing"
            self._emit_status()
            self._scheduler.later(100, lambda: self._start_next(activity))
            return activity.activity_id
        return self._respond("tests.run", position, run, test_ids=list(test_ids))

    def abort(self, activity_id: str) -> bool:
        activity = self.runs.get(activity_id)
        if activity is None:
            return False
        activity.aborted = True
        return True

    def end_all(self, error: ApiError) -> None:
        for activity in list(self.runs.values()):
            self._finish(activity, error)

    def _progress(self, activity: TestRunState, test_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        self._emit(ActivityProgress(activity.activity_id, activity.position, activity.index + 1,
                                    len(activity.test_ids), _SAMPLES[test_id][0], test_id, result=result))

    def _start_next(self, activity: TestRunState) -> None:
        if self._stopped(activity):
            return
        if activity.index >= len(activity.test_ids):
            self._finish(activity, None)
            return
        test_id = activity.test_ids[activity.index]
        started = self._host.clock()
        self._progress(activity, test_id)
        self._scheduler.later(_SAMPLES[test_id][1], lambda: self._end_test(activity, test_id, started))

    def _end_test(self, activity: TestRunState, test_id: str, started: float) -> None:
        if self._stopped(activity):
            return
        _, run_ms, passed, note, output = _SAMPLES[test_id]
        passed = self.outcomes.get(test_id, passed)
        result = {"id": test_id, "passed": passed, "started": started, "duration_s": run_ms / 1000,
                  "notes": "" if passed else (note or "Failed"), "output": list(output)}
        activity.results.append(result)
        self._progress(activity, test_id, result)
        activity.index += 1
        self._scheduler.later(100, lambda: self._start_next(activity))

    def _stopped(self, activity: TestRunState) -> bool:
        """Stopping, or losing the DUT, ends the run before the next step."""
        if activity.activity_id not in self.runs:   # already ended (station restart)
            return True
        if activity.aborted:
            self._finish(activity, ApiError(ErrorCode.ABORTED, "Stopped by user"))
        elif not self._host.facts[activity.position].dut_connected:
            self._finish(activity, ApiError(ErrorCode.DUT_DISCONNECTED, f"DUT {activity.position} disconnected"))
        else:
            return False
        return True

    def _finish(self, activity: TestRunState, error: Optional[ApiError]) -> None:
        self.runs.pop(activity.activity_id, None)
        self._host.facts[activity.position].activity = "idle"
        self._emit_status()
        self._emit(ActivityFinished(activity.activity_id, activity.position, error is None, activity.results, error))


class StationTestMethods:
    """FakeStationGateway's tests.* methods; the work is in its FakeStationTests."""
    station_tests: FakeStationTests

    def list_tests(self) -> Call[List[StationTest]]:
        return self.station_tests.list_tests()

    def run_tests(self, position: int, test_ids: List[str]) -> Call[str]:
        return self.station_tests.run_tests(position, test_ids)
