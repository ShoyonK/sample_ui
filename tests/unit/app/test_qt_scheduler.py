"""QtScheduler.every keeps its rate: the data logger's polling depends on it (req 17)."""

import statistics
import time

import pytest
from PyQt5.QtCore import QEventLoop, QTimer

from sibench_ui.app.qt_scheduler import PRECISE_BELOW_MS, QtScheduler
from sibench_ui.shared.qt import COARSE_TIMER, PRECISE_TIMER


def _timer_of(handle):
    return handle._timer


def test_short_intervals_use_the_precise_timer(qapp):
    scheduler = QtScheduler()
    short, long = scheduler.every(50, lambda: None), scheduler.every(PRECISE_BELOW_MS, lambda: None)
    try:
        assert _timer_of(short).timerType() == PRECISE_TIMER
        assert _timer_of(long).timerType() == COARSE_TIMER
    finally:
        short.cancel()
        long.cancel()


@pytest.mark.parametrize("ms", [50, 20, 10])
def test_a_repeating_timer_fires_at_the_rate_asked_for(qapp, ms):
    """Qt's coarse timer on Windows snaps to the ~15.6 ms system tick: 50 ms ran at 62.5 ms (16 Hz, not 20).

    Checks the median gap between ticks, not the tick count: a busy machine can stall the event loop for a moment,
    which loses ticks from a count but barely moves the median. The coarse timer's gaps are 1.25 to 1.56 times
    the interval, well past the 1.15 allowed here.
    """
    ticks = []
    handle = QtScheduler().every(ms, lambda: ticks.append(time.perf_counter()))
    loop = QEventLoop()
    QTimer.singleShot(1000, loop.quit)
    loop.exec_()
    handle.cancel()
    assert len(ticks) >= 5, f"only {len(ticks)} ticks in 1 s at {ms} ms"
    gap_ms = statistics.median(b - a for a, b in zip(ticks, ticks[1:])) * 1000
    assert gap_ms <= ms * 1.15, f"ticks every {gap_ms:.1f} ms when asked for {ms} ms"
