"""What the client needs from its owner: timers, and a way to run work on the owner's thread.

The client never makes threads of its own beyond the socket's reader and the connect attempt; everything else
runs where `post` puts it. A GUI passes its event loop's timers and a poster onto the GUI thread; a script can
pass a simple thread-based scheduler.
"""

from __future__ import annotations

from typing import Callable

from typing_extensions import Protocol


class Cancellable(Protocol):
    def cancel(self) -> None: ...


class Handle:
    """What later()/every() return; cancel() stops a task that hasn't run (or stops repeating)."""

    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class Timers(Protocol):
    """Runs a callback after `ms`, or every `ms`, on the owner's thread (or anywhere: the client posts what it
    does from a timer)."""

    def later(self, ms: int, fn: Callable[[], None]) -> Cancellable: ...
    def every(self, ms: int, fn: Callable[[], None]) -> Cancellable: ...


Post = Callable[[Callable[[], None]], None]   # runs a function on the owner's thread
