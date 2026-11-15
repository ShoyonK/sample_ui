"""Schedulers decouple timing from Qt so tests control time exactly (no sleeps)."""

from __future__ import annotations

import heapq
import itertools
from typing import Callable, List, NamedTuple, Protocol

from station_client.timers import Handle   # the same Handle the station client's timers return


class Scheduler(Protocol):
    """Runs a callback after `ms`, or every `ms`. QtScheduler in the app, ManualScheduler in tests."""

    def later(self, ms: int, fn: Callable[[], None]) -> Handle: ...
    def every(self, ms: int, fn: Callable[[], None]) -> Handle: ...


class _Task(NamedTuple):
    due: int
    seq: int                   # insertion order: ties on `due` run first-in first-out
    fn: Callable[[], None]
    handle: Handle
    period: int                # 0 for a one-shot task


class ManualScheduler:
    """Deterministic scheduler for tests. `later(0, fn)` runs immediately."""

    def __init__(self) -> None:
        self.now_ms = 0
        self._queue: List[_Task] = []
        self._seq = itertools.count()

    def later(self, ms: int, fn: Callable[[], None]) -> Handle:
        handle = Handle()
        if ms <= 0:
            fn()
            return handle
        heapq.heappush(self._queue, _Task(self.now_ms + ms, next(self._seq), fn, handle, 0))
        return handle

    def every(self, ms: int, fn: Callable[[], None]) -> Handle:
        handle = Handle()
        heapq.heappush(self._queue, _Task(self.now_ms + ms, next(self._seq), fn, handle, max(1, ms)))
        return handle

    def advance(self, ms: int) -> None:
        """Moves time forward by `ms`, running every task that falls due, in time order."""
        target = self.now_ms + ms
        while self._queue and self._queue[0].due <= target:
            task = heapq.heappop(self._queue)
            self.now_ms = task.due
            if task.handle.cancelled:
                continue
            if task.period:
                heapq.heappush(self._queue, task._replace(due=task.due + task.period, seq=next(self._seq)))
            task.fn()
        self.now_ms = target

    def run_pending(self, max_steps: int = 10_000) -> None:
        """Runs one-shot tasks until none are left. Repeating tasks are not run."""
        for _ in range(max_steps):
            one_shots = [task for task in self._queue if not task.period and not task.handle.cancelled]
            if not one_shots:
                return
            self.advance(min(task.due for task in one_shots) - self.now_ms)
