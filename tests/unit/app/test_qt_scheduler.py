"""QtScheduler.every keeps its rate: the data logger's polling depends on it (req 17)."""

import time

import pytest
from PyQt5.QtCore import QEventLoop, QTimer

from sirat_ui.app.qt_scheduler import PRECISE_BELOW_MS, QtScheduler
from sirat_ui.shared.qt import COARSE_TIMER, PRECISE_TIMER


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
    """Qt's coarse timer on Windows snaps to the ~15.6 ms system tick: 50 ms ran at 62.5 ms (16 Hz, not 20)."""
    ticks = []
    handle = QtScheduler().every(ms, lambda: ticks.append(time.perf_counter()))
    loop = QEventLoop()
    QTimer.singleShot(1000, loop.quit)
    loop.exec_()
    handle.cancel()
    expected = 1000 / ms
    assert len(ticks) >= expected * 0.85, f"{len(ticks)} ticks in 1 s at {ms} ms, expected about {expected:.0f}"
