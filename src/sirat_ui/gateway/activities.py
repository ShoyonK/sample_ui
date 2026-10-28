"""ActivityTracker: hands each activity.progress / activity.finished event to whoever started that activity.

Sequence runs, chamber waits and ECA captures all report this way; the starter calls follow() with the
activity id the start call returned, and stops hearing about it once it finishes.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

from sirat_ui.gateway.port import EventSource
from sirat_ui.models.station import ActivityFinished, ActivityProgress

Progress = Callable[[ActivityProgress], None]
Done = Callable[[ActivityFinished], None]


class ActivityTracker:
    def __init__(self, source: EventSource) -> None:
        self._followed: Dict[str, Tuple[Progress, Done]] = {}
        source.events.connect(self._on_event)

    def follow(self, activity_id: str, on_progress: Progress, on_done: Done) -> None:
        self._followed[activity_id] = (on_progress, on_done)

    def _on_event(self, event: object) -> None:
        if isinstance(event, ActivityProgress) and event.activity_id in self._followed:
            self._followed[event.activity_id][0](event)
        elif isinstance(event, ActivityFinished) and event.activity_id in self._followed:
            self._followed.pop(event.activity_id)[1](event)
