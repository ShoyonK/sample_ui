"""Scheduler backed by QTimer, used when the app runs for real."""

from __future__ import annotations

from typing import Callable, List

from PyQt5.QtCore import QTimer

from sirat_ui.gateway.scheduler import Handle


class _TimerHandle(Handle):
    def __init__(self, timer: QTimer) -> None:
        super().__init__()
        self._timer = timer

    def cancel(self) -> None:
        super().cancel()
        self._timer.stop()


class QtScheduler:
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
        timer.timeout.connect(fn)
        timer.start()
        self._timers = [t for t in self._timers if t.isActive()] + [timer]
        return _TimerHandle(timer)
