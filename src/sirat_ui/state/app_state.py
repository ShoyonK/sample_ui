"""AppState: the single source of truth for state shared across tabs.

Pure Python (no Qt) so services can use it. StateViewModel mirrors it for QML.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union

from sirat_ui.core.observable import Event
from sirat_ui.core.registers import ChipInfo, PeripheralDef, RegisterDef
from sirat_ui.core.requires import PositionFacts, check_requires
from sirat_ui.gateway.models import StationStatus
from sirat_ui.state.preferences import Preferences

Selection = Union[RegisterDef, PeripheralDef, None]


class AppState:
    def __init__(self, preferences: Optional[Preferences] = None, backend_label: str = "") -> None:
        self.preferences = preferences or Preferences()
        self.position = self.preferences.last_position or 1
        self.backend_label = backend_label
        self.release_id = ""
        self.protocol: Optional[int] = None
        self.connecting = False
        self.status_message = "Ready"
        self.selection: Selection = None
        self._facts: Dict[int, PositionFacts] = {}
        self._chips: Dict[int, ChipInfo] = {}

        self.changed = Event()              # facts, chip, connecting, status message
        self.selection_changed = Event()    # (selection, by_user: bool)
        self.disconnected = Event()         # (position, cause, detected_by)
        self.preferences_changed = Event()  # (preferences)

    # ---- facts -------------------------------------------------------------

    @property
    def facts(self) -> PositionFacts:
        return self._facts.get(self.position) or PositionFacts(self.position)

    @property
    def connected(self) -> bool:
        return self.facts.dut_connected

    @property
    def chip(self) -> Optional[ChipInfo]:
        return self._chips.get(self.position)

    def apply_status(self, status: StationStatus) -> None:
        self.release_id = status.release_id
        for facts in status.positions:
            self._facts[facts.position] = facts
        self.changed.emit()

    def set_chip(self, position: int, chip: Optional[ChipInfo]) -> None:
        if chip is None:
            self._chips.pop(position, None)
        else:
            self._chips[position] = chip
        self.changed.emit()

    def set_connecting(self, connecting: bool) -> None:
        self.connecting = connecting
        self.changed.emit()

    def set_position(self, position: int) -> None:
        if position != self.position:
            self.position = position
            self.update_preferences(last_position=position)
            self.changed.emit()

    def mark_disconnected(self, position: int, cause: str, detected_by: str) -> None:
        facts = self._facts.setdefault(position, PositionFacts(position))
        facts.dut_connected = False
        facts.phy = None
        facts.watching = False
        self.disconnected.emit(position, cause, detected_by)
        self.changed.emit()

    def missing(self, method: str) -> List[str]:
        return check_requires(method, self.facts)

    def can(self, method: str) -> bool:
        return not self.missing(method)

    def set_status_message(self, text: str) -> None:
        self.status_message = text
        self.changed.emit()

    # ---- selection -----------------------------------------------------------

    def select(self, selection: Selection, by_user: bool = True) -> None:
        self.selection = selection
        self.selection_changed.emit(selection, by_user)

    @property
    def selected_register(self) -> Optional[RegisterDef]:
        return self.selection if isinstance(self.selection, RegisterDef) else None

    # ---- preferences ----------------------------------------------------------

    def update_preferences(self, **changes) -> None:
        for key, value in changes.items():
            setattr(self.preferences, key, value)
        self.preferences_changed.emit(self.preferences)
