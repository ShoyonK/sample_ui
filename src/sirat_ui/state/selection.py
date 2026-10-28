"""SelectionState: the register or peripheral the user has open (tree, favorites, Ctrl+K, watch list)."""

from __future__ import annotations

from typing import Optional, Union

from sirat_ui.core.observable import Event
from sirat_ui.models.registers import PeripheralDef, RegisterDef

Selection = Union[RegisterDef, PeripheralDef, None]


class SelectionState:
    def __init__(self) -> None:
        self.current: Selection = None
        self.changed = Event()   # (selection, by_user: bool)

    def select(self, selection: Selection, by_user: bool = True) -> None:
        self.current = selection
        self.changed.emit(selection, by_user)

    @property
    def register(self) -> Optional[RegisterDef]:
        return self.current if isinstance(self.current, RegisterDef) else None
