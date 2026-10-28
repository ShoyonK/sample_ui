"""Runs automation.seq ops in the fake, one step per scheduler tick, with progress events."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from sirat_ui.core.ops import describe_op, op_kind
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.scheduler import Scheduler
from sirat_ui.models.station import ActivityFinished, ActivityProgress

STEP_MS = 450


class FakeActivity:
    def __init__(self, activity_id: str, position: int, ops: List[Dict[str, Any]], stop_on_error: bool) -> None:
        self.activity_id = activity_id
        self.position = position
        self.ops = ops
        self.stop_on_error = stop_on_error
        self.step = 0
        self.results: List[Dict[str, Any]] = []
        self.aborted = False
        self.finished = False


class FakeSequencer:
    def __init__(self, scheduler: Scheduler, emit: Callable[[Any], None],
                 execute: Callable[[int, Dict[str, Any]], Any], on_done: Callable[[FakeActivity], None]) -> None:
        self._scheduler = scheduler
        self._emit = emit
        self._execute = execute
        self._on_done = on_done
        self.activities: Dict[str, FakeActivity] = {}

    def start(self, activity: FakeActivity) -> None:
        self.activities[activity.activity_id] = activity
        self._scheduler.later(STEP_MS, lambda: self._next(activity))

    def abort(self, activity_id: str) -> None:
        activity = self.activities.get(activity_id)
        if activity and not activity.finished:
            activity.aborted = True

    def _next(self, activity: FakeActivity) -> None:
        if activity.aborted:
            self._finish(activity, False, ApiError(ErrorCode.ABORTED, "Aborted by user"))
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
        self._on_done(activity)
        self._emit(ActivityFinished(activity.activity_id, activity.position, ok, activity.results, error))
