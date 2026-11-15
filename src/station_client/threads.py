"""ThreadScheduler: timers (station_client.timers.Timers) that run every task on one thread of its own.

For a tool or test with no event loop of its own: pass it as a Link's timers. The SiRAT fake station uses it too
(it isn't thread-safe, so FakeStationServer runs everything it does here). later(), every() and run() may be
called from any thread.
"""

from __future__ import annotations

import heapq
import itertools
import threading
import time
from typing import Any, Callable, List, Optional, Tuple, TypeVar

from station_client.timers import Handle

T = TypeVar("T")


class ThreadScheduler:
    """See the module docstring. start() before use; stop() ends the thread (tasks not yet due are dropped)."""

    def __init__(self, name: str = "station") -> None:
        self._name = name
        self._queue: List[Tuple[float, int, Callable[[], None], Handle, float]] = []
        self._seq = itertools.count()
        self._wake = threading.Condition()
        self._thread: Optional[threading.Thread] = None
        self._stopping = False
        self.errors: List[BaseException] = []   # exceptions tasks raised (tests check it stays empty)

    def start(self) -> "ThreadScheduler":
        self._thread = threading.Thread(target=self._loop, name=self._name, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        with self._wake:
            self._stopping = True
            self._wake.notify()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)

    @property
    def on_thread(self) -> bool:
        return threading.current_thread() is self._thread

    def later(self, ms: int, fn: Callable[[], None]) -> Handle:
        return self._push(max(0, ms) / 1000, fn, 0.0)

    def every(self, ms: int, fn: Callable[[], None]) -> Handle:
        period = max(1, ms) / 1000
        return self._push(period, fn, period)

    def run(self, fn: Callable[[], T], timeout: float = 5.0) -> T:
        """Runs fn on the scheduler's thread and returns its result (or raises what it raised)."""
        if self.on_thread:
            return fn()
        done = threading.Event()
        box: List[Any] = []

        def task() -> None:
            try:
                box.append((True, fn()))
            except BaseException as exc:   # handed back to the caller
                box.append((False, exc))
            done.set()

        self.later(0, task)
        if not done.wait(timeout):
            raise TimeoutError(f"{self._name} didn't run the task within {timeout} s")
        ok, value = box[0]
        if not ok:
            raise value
        return value

    def _push(self, delay_s: float, fn: Callable[[], None], period: float) -> Handle:
        handle = Handle()
        with self._wake:
            heapq.heappush(self._queue, (time.monotonic() + delay_s, next(self._seq), fn, handle, period))
            self._wake.notify()
        return handle

    def _loop(self) -> None:
        while True:
            with self._wake:
                while not self._stopping and (not self._queue or self._queue[0][0] > time.monotonic()):
                    timeout = self._queue[0][0] - time.monotonic() if self._queue else None
                    self._wake.wait(timeout)
                if self._stopping:
                    return
                due, _, fn, handle, period = heapq.heappop(self._queue)
                if period and not handle.cancelled:
                    # the next run counts from when this one was due, so the rate doesn't drift
                    heapq.heappush(self._queue, (max(due + period, time.monotonic()), next(self._seq), fn, handle,
                                                 period))
            if handle.cancelled:
                continue
            try:
                fn()
            except Exception as exc:   # one bad task mustn't stop the station
                self.errors.append(exc)
