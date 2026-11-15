"""Scheduler backed by QTimer, used when the app runs for real."""

from __future__ import annotations

from typing import Callable, List

from PyQt5.QtCore import QTimer

from sibench_ui.gateway.scheduler import Handle
from sibench_ui.shared.qt import PRECISE_TIMER

# Below this, repeating timers use Qt's precise timer. Qt's default (coarse) timer on Windows runs on the system
# clock tick of about 15.6 ms, so a 50 ms interval fires every 62.5 ms and a 20 ms one every 31 ms: the data logger
# recorded 16 Hz when asked for 20. Longer intervals keep the coarse timer, where the tick is a small error.
PRECISE_BELOW_MS = 1000


class _TimerHandle(Handle):
    def __init__(self, timer: QTimer) -> None:
        super().__init__()
        self._timer = timer

    def cancel(self) -> None:
        super().cancel()
        self._timer.stop()


class QtScheduler:
    """The app's Scheduler. every() keeps its QTimers referenced, or PyQt would garbage-collect (and stop) them."""

    def __init__(self) -> None:
        self._timers: List[QTimer] = []

    def later(self, ms: int, fn: Callable[[], None]) -> Handle:
        handle = Handle()

        def fire() -> None:
            if not handle.cancelled:
                fn()

        QTimer.singleShot(max(0, ms), fire)
        return handle

    def every(self, ms: int, fn: Callable[[], None]) -> Handle:
        timer = QTimer()
        timer.setInterval(max(1, ms))
        if ms < PRECISE_BELOW_MS:
            timer.setTimerType(PRECISE_TIMER)
        timer.timeout.connect(fn)
        timer.start()
        self._timers = [t for t in self._timers if t.isActive()] + [timer]
        return _TimerHandle(timer)
