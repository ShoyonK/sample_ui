"""PreferencesState: the user's preferences (~/.sirat/preferences.json) and who to tell when they change."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Optional

from sirat_ui.core.observable import Event
from sirat_ui.models.settings import Preferences


class PreferencesState:
    """The current Preferences; `changed` fires with them after every update (the container saves them)."""

    def __init__(self, preferences: Optional[Preferences] = None) -> None:
        self.value = preferences or Preferences()
        self.changed = Event()   # (preferences)

    def update(self, **changes: Any) -> None:
        """Sets preference fields by name and emits `changed` once.

        Raises:
            AttributeError: A key isn't a Preferences field (a typo would otherwise be silently kept and lost).
        """
        known = {f.name for f in fields(self.value)}
        unknown = set(changes) - known
        if unknown:
            raise AttributeError(f"Unknown preference(s): {', '.join(sorted(unknown))}")
        for key, value in changes.items():
            setattr(self.value, key, value)
        self.changed.emit(self.value)
