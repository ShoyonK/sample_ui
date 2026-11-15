"""Runs automation.seq ops in the fake, one step per scheduler tick, with progress events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sibench_ui.core.ops import describe_op, op_kind
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.scheduler import Scheduler
from sibench_ui.models.station import ActivityFinished, ActivityProgress

STEP_MS = 450


@dataclass
class FakeActivity:
    """One automation.seq.run: its ops, how far it got, and how it ended."""
    activity_id: str
    position: int
    ops: List[Dict[str, Any]]
    stop_on_error: bool
    step: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    aborted: bool = False
    finished: bool = False
    error: Optional[ApiError] = None


class FakeSequencer:
    """Runs one op per STEP_MS, emitting progress before each and finished at the end (or on error/abort)."""

    def __init__(self, scheduler: Scheduler, emit: Callable[[Any], None],
                 execute: Callable[[int, Dict[str, Any]], Any], on_done: Callable[[FakeActivity], None],
                 dut_connected: Callable[[int], bool] = lambda position: True) -> None:
        self._scheduler = scheduler
        self._emit = emit
        self._execute = execute
        self._on_done = on_done
        self._dut_connected = dut_connected
        self.activities: Dict[str, FakeActivity] = {}

    def start(self, activity: FakeActivity) -> None:
        self.activities[activity.activity_id] = activity
        self._scheduler.later(STEP_MS, lambda: self._next(activity))

    def abort(self, activity_id: str) -> None:
        activity = self.activities.get(activity_id)
        if activity and not activity.finished:
            activity.aborted = True

    def end_all(self, error: ApiError) -> None:
        for activity in list(self.activities.values()):
            if not activity.finished:
                self._finish(activity, False, error)

    def _next(self, activity: FakeActivity) -> None:
        if activity.finished:
            return
        if activity.aborted:
            self._finish(activity, False, ApiError(ErrorCode.ABORTED, "Aborted by user"))
            return
        if not self._dut_connected(activity.position):
            self._finish(activity, False, ApiError(ErrorCode.DUT_DISCONNECTED, f"DUT {activity.position} disconnected"))
            return
        if activity.step >= len(activity.ops):
            self._finish(activity, True)
            return
        op = activity.ops[activity.step]
        self._emit(ActivityProgress(activity.activity_id, activity.position, activity.step + 1,
                                    len(activity.ops), describe_op(op), str(op.get("group", ""))))
        try:
            value = self._execute(activity.position, op)
            activity.results.append({"ok": True, "value": value, "kind": op_kind(op)})
        except ApiError as exc:
            activity.results.append({"ok": False, "error": exc.message, "kind": op_kind(op)})
            if activity.stop_on_error:
                self._finish(activity, False, exc)
                return
        activity.step += 1
        self._scheduler.later(STEP_MS, lambda: self._next(activity))

    def _finish(self, activity: FakeActivity, ok: bool, error: Optional[ApiError] = None) -> None:
        activity.finished = True
        activity.error = error
        self._on_done(activity)
        self._emit(ActivityFinished(activity.activity_id, activity.position, ok, activity.results, error))
