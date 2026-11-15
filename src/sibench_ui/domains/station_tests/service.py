"""Test execution (req 33): run the selected tests in order, follow progress, collect results, export them.

The station lists the tests (tests.list) and runs them as an activity (tests.run). Each test reports as it starts
and again with its result (pass or fail, notes, output) as it ends, so results fill in while the run goes on.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sibench_ui.core.observable import Event
from sibench_ui.domains.logs.service import LogService
from sibench_ui.gateway.activities import ActivityTracker
from sibench_ui.gateway.errors import ApiError
from sibench_ui.gateway.port import TestsPort
from sibench_ui.gateway.scheduler import Handle, Scheduler
from sibench_ui.models.station import ActivityFinished, ActivityProgress, StationTest
from sibench_ui.shared.error_presenter import ErrorPresenter
from sibench_ui.state.station import StationState


@dataclass
class TestResult:
    """One finished test."""
    test: StationTest
    passed: bool
    started: float
    duration_s: float
    notes: str = ""
    output: List[str] = field(default_factory=list)


@dataclass
class TestRun:
    """A run of the selected tests: which one is going, and the results so far."""
    tests: List[StationTest]
    position: int
    started: float
    activity_id: Optional[str] = None
    running: bool = True
    finished: Optional[float] = None
    current: Optional[StationTest] = None
    results: List[TestResult] = field(default_factory=list)
    stop_reason: str = ""             # why the run ended early, or "" if every test ran

    def summary(self) -> str:
        passed = sum(1 for r in self.results if r.passed)
        return f"{passed} passed, {len(self.results) - passed} failed"


class StationTestService:
    """The station's tests and one run at a time (see the module docstring)."""

    def __init__(self, gateway: TestsPort, state: StationState, activities: ActivityTracker, errors: ErrorPresenter,
                 log: LogService, scheduler: Scheduler, clock: Callable[[], float] = time.time) -> None:
        self._gateway = gateway
        self._state = state
        self._activities = activities
        self._errors = errors
        self._log = log
        self._scheduler = scheduler
        self._clock = clock
        self._ticker: Optional[Handle] = None
        self.tests: List[StationTest] = []
        self.loaded = False
        self.load_error = ""
        self.run: Optional[TestRun] = None
        self.changed = Event()     # the list of tests
        self.progress = Event()    # the run; also every half second while running, for the elapsed time

    def load(self) -> None:
        def loaded(tests: List[StationTest]) -> None:
            self.tests, self.loaded, self.load_error = list(tests), True, ""
            self.changed.emit()

        def failed(error: ApiError) -> None:
            self.loaded, self.load_error = True, error.message
            self._errors.present(error, "List tests")
            self.changed.emit()

        self._gateway.list_tests().then(loaded, failed)

    def elapsed_s(self) -> float:
        run = self.run
        return 0.0 if run is None else (run.finished or self._clock()) - run.started

    def start(self, test_ids: List[str]) -> None:
        """Runs the tests with these ids, in the station's order. Ignored while a run is going."""
        wanted = set(test_ids)
        tests = [t for t in self.tests if t.id in wanted]   # in the station's order
        if not tests or (self.run is not None and self.run.running):
            return
        run = TestRun(tests, self._state.position, self._clock())
        self.run = run
        self._log.info(f"Test run started on DUT {run.position}: {len(tests)} test(s)")
        self.progress.emit()

        def started(activity_id: str) -> None:
            run.activity_id = activity_id
            self._activities.follow(activity_id, self._on_progress, self._on_finished)
            self._ticker = self._scheduler.every(500, self.progress.emit)

        def failed(error: ApiError) -> None:
            run.running, run.finished, run.stop_reason = False, self._clock(), "Couldn't start"
            self._errors.present(error, "Run tests")
            self.progress.emit()

        self._gateway.run_tests(run.position, [t.id for t in tests]).then(started, failed)

    def stop(self) -> None:
        run = self.run
        if run is not None and run.running and run.activity_id:
            run.stop_reason = "Stopping…"
            self._gateway.abort_activity(run.activity_id)
            self.progress.emit()

    def _on_progress(self, event: ActivityProgress) -> None:
        run = self.run
        if run is None:
            return
        test = next((t for t in run.tests if t.id == event.group), None)
        if test is None:
            return
        if event.result is None:
            run.current = test
        else:
            result = event.result
            run.results.append(TestResult(test, bool(result.get("passed")), float(result.get("started", 0.0)),
                                          float(result.get("duration_s", 0.0)), str(result.get("notes", "")),
                                          [str(line) for line in result.get("output", [])]))
            run.current = None
        self.progress.emit()

    def _on_finished(self, event: ActivityFinished) -> None:
        run = self.run
        if run is None:
            return
        if self._ticker is not None:
            self._ticker.cancel()
            self._ticker = None
        run.running, run.finished, run.current = False, self._clock(), None
        run.stop_reason = "" if event.ok else (event.error.message if event.error else "Stopped")
        ended = "finished" if event.ok else f"stopped ({run.stop_reason})"
        if event.ok and all(r.passed for r in run.results):
            self._log.success(f"Test run {ended}: {run.summary()}")
        else:
            self._log.warning(f"Test run {ended}: {run.summary()}")
        self.progress.emit()

    def export(self, path: Path) -> None:
        """Req 33 results storage: JSON with test metadata, timestamps, status and output."""
        run = self.run
        if run is None:
            raise ValueError("No results to export")

        def stamp(ts: Optional[float]) -> Optional[str]:
            if ts is None:
                return None
            return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts)) + f".{int(ts * 1000) % 1000:03d}"

        data: Dict[str, Any] = {
            "dut_position": run.position,
            "started": stamp(run.started),
            "finished": stamp(run.finished),
            "tests": [{"id": r.test.id, "name": r.test.name, "status": "pass" if r.passed else "fail",
                       "started": stamp(r.started), "duration_s": r.duration_s, "notes": r.notes,
                       "output": r.output} for r in run.results],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._log.info(f"Test results exported to {path}")
