"""Schedulers decouple timing from Qt so tests control time exactly (no sleeps)."""

from __future__ import annotations

import heapq
import itertools
from typing import Callable, List, Protocol, Tuple


class Handle:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class Scheduler(Protocol):
    def later(self, ms: int, fn: Callable[[], None]) -> Handle: ...
    def every(self, ms: int, fn: Callable[[], None]) -> Handle: ...


class ManualScheduler:
    """Deterministic scheduler for tests. `later(0, fn)` runs immediately."""

    def __init__(self) -> None:
        self.now_ms = 0
        self._queue: List[Tuple[int, int, Callable[[], None], Handle, int]] = []
        self._seq = itertools.count()

    def later(self, ms: int, fn: Callable[[], None]) -> Handle:
        handle = Handle()
        if ms <= 0:
            fn()
            return handle
        heapq.heappush(self._queue, (self.now_ms + ms, next(self._seq), fn, handle, 0))
        return handle

    def every(self, ms: int, fn: Callable[[], None]) -> Handle:
        handle = Handle()
        heapq.heappush(self._queue, (self.now_ms + ms, next(self._seq), fn, handle, max(1, ms)))
        return handle

    def advance(self, ms: int) -> None:
        target = self.now_ms + ms
        while self._queue and self._queue[0][0] <= target:
            due, _, fn, handle, period = heapq.heappop(self._queue)
            self.now_ms = due
            if handle.cancelled:
                continue
            if period:
                heapq.heappush(self._queue, (due + period, next(self._seq), fn, handle, period))
            fn()
        self.now_ms = target

    def run_pending(self, max_steps: int = 10_000) -> None:
        """Runs one-shot tasks until none are left. Repeating tasks are not run."""
        for _ in range(max_steps):
            one_shots = [item for item in self._queue if not item[4] and not item[3].cancelled]
            if not one_shots:
                return
            self.advance(min(item[0] for item in one_shots) - self.now_ms)
