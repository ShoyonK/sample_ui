"""StationState: what the station says about the bench, for the DUT position the GUI is looking at.

Facts per position, chips, instruments, the connecting flag and the requires checks built on them. Pure Python
(no Qt) so services can use it; StateViewModel mirrors it for QML. Selection, preferences and the status line
are separate stores (state/selection.py, state/preferences.py, state/status.py) with their own events.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.core.requires import check_requires
from sirat_ui.models.facts import InstrumentFacts, PositionFacts
from sirat_ui.models.registers import ChipInfo
from sirat_ui.models.station import StationStatus


class StationState:
    def __init__(self, position: int = 1, backend_label: str = "") -> None:
        self.position = position or 1
        self.backend_label = backend_label
        self.release_id = ""
        self.protocol: Optional[int] = None
        self.connecting = False
        self._facts: Dict[int, PositionFacts] = {}
        self.instruments: List[InstrumentFacts] = []
        self._chips: Dict[int, ChipInfo] = {}

        self.changed = Event()              # facts, chips, instruments, connecting, position
        self.disconnected = Event()         # (position, cause, detected_by)
        self.position_changed = Event()     # (position)

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
        self.instruments = list(status.instruments)
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
            self.position_changed.emit(position)
            self.changed.emit()

    def mark_disconnected(self, position: int, cause: str, detected_by: str) -> None:
        facts = self._facts.setdefault(position, PositionFacts(position))
        facts.dut_connected = False
        facts.phy = None
        facts.watching = False
        self.disconnected.emit(position, cause, detected_by)
        self.changed.emit()

    def facts_for(self, position: int) -> PositionFacts:
        return self._facts.get(position) or PositionFacts(position)

    def missing(self, method: str, instrument_id: Optional[str] = None) -> List[str]:
        return check_requires(method, self.facts, self.instruments, instrument_id)

    def can(self, method: str, instrument_id: Optional[str] = None) -> bool:
        return not self.missing(method, instrument_id)

    def instrument(self, kind: str) -> Optional[InstrumentFacts]:
        """The bench's instrument of that kind: the first connected one, else the first one listed."""
        of_kind = [i for i in self.instruments if i.kind == kind]
        return next((i for i in of_kind if i.connected), of_kind[0] if of_kind else None)
