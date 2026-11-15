"""QtPoster: runs a function on the GUI thread, from any thread.

ApiStationGateway reads the station's socket on a thread of its own; it hands each message to post() so that
replies resolve their Call and events are emitted on the GUI thread, as gateway/call.py promises.

It relies on Qt's default (auto) connection: a signal emitted on another thread is queued to the receiver's
thread (the GUI thread, where the poster is created); one emitted on the GUI thread runs at once.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class QtPoster(QObject):
    """Create it on the GUI thread; post(fn) from any thread runs fn there, in order."""

    _posted = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._posted.connect(self._run)

    def post(self, fn: Callable[[], None]) -> None:
        self._posted.emit(fn)

    @pyqtSlot(object)
    def _run(self, fn: Callable[[], None]) -> None:
        fn()
