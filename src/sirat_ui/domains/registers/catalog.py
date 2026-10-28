"""RegisterCatalog: the peripheral tree, fetched once per connection and cached (API doc: registers.tree)."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sirat_ui.core import search as search_mod
from sirat_ui.core.observable import Event
from sirat_ui.core.registers import FieldDef, PeripheralDef, RegisterDef
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.port import StationGateway
from sirat_ui.state.app_state import AppState


class RegisterCatalog:
    def __init__(self, gateway: StationGateway, state: AppState) -> None:
        self._gateway = gateway
        self._state = state
        self.peripherals: List[PeripheralDef] = []
        self._registers: Dict[str, RegisterDef] = {}
        self._by_peripheral: Dict[str, PeripheralDef] = {}
        self.loaded = Event()

    def load(self, position: int) -> Call:
        return self._gateway.register_tree(position).map(self._set)

    def _set(self, peripherals: List[PeripheralDef]) -> List[PeripheralDef]:
        self.peripherals = sorted(peripherals, key=lambda p: p.name)
        self._by_peripheral = {p.name: p for p in self.peripherals}
        self._registers = {r.full_name: r for p in self.peripherals for r in p.registers}
        self.loaded.emit()
        return self.peripherals

    def clear(self) -> None:
        self._set([])

    def peripheral(self, name: str) -> Optional[PeripheralDef]:
        return self._by_peripheral.get(name)

    def register(self, full_name: str) -> Optional[RegisterDef]:
        return self._registers.get(full_name)

    def resolve(self, full_name: str) -> Tuple[Optional[RegisterDef], Optional[FieldDef]]:
        """Accepts REG or REG.FIELD (e.g. "MODEM.CTRL" or "MODEM.CTRL.OPMODE")."""
        reg = self._registers.get(full_name)
        if reg:
            return reg, None
        reg_name, _, field_name = full_name.rpartition(".")
        reg = self._registers.get(reg_name)
        if reg and reg.field(field_name):
            return reg, reg.field(field_name)
        return None, None

    def search(self, text: str) -> search_mod.SearchResult:
        return search_mod.search(self.peripherals, text, self._state.preferences.show_secure_peripherals)
