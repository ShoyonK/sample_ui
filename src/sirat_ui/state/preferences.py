"""PreferencesState: the user's preferences (~/.sirat/preferences.json) and who to tell when they change."""

from __future__ import annotations

from typing import Any, Optional

from sirat_ui.core.observable import Event
from sirat_ui.models.settings import Preferences


class PreferencesState:
    def __init__(self, preferences: Optional[Preferences] = None) -> None:
        self.value = preferences or Preferences()
        self.changed = Event()   # (preferences)

    def update(self, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(self.value, key, value)
        self.changed.emit(self.value)
