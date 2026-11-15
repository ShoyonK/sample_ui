"""A tiny observer so services can publish changes without depending on Qt."""

from __future__ import annotations

from typing import Any, Callable, List


class Event:
    """A list of callbacks. emit() calls them synchronously, in the order they connected.

    emit() iterates over a copy, so a callback may disconnect itself (or connect another) while being called.
    """

    def __init__(self) -> None:
        self._subscribers: List[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        self._subscribers.append(callback)
        return callback

    def disconnect(self, callback: Callable[..., Any]) -> None:
        """Removes a callback; does nothing if it isn't connected."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._subscribers):
            callback(*args, **kwargs)
