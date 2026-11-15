"""RegisterCatalog: the selected DUT's peripheral tree, fetched on connect and on switching DUT, and cached
(API doc: registers.tree). Each DUT can be a different chip, so the tree is never shared between positions."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sibench_ui.core import search as search_mod
from sibench_ui.core.observable import Event
from sibench_ui.gateway.call import Call
from sibench_ui.gateway.port import RegistersPort
from sibench_ui.models.registers import FieldDef, PeripheralDef, RegisterDef, SearchResult
from sibench_ui.state.preferences import PreferencesState


class RegisterCatalog:
    """The connected DUT's peripheral tree, with lookups by name. `loaded` fires whenever it's replaced."""

    def __init__(self, gateway: RegistersPort, prefs: PreferencesState) -> None:
        self._gateway = gateway
        self._prefs = prefs
        self.peripherals: List[PeripheralDef] = []
        self._registers: Dict[str, RegisterDef] = {}
        self._by_peripheral: Dict[str, PeripheralDef] = {}
        self._generation = 0     # bumped by every load and clear, so only the latest one lands
        self.loaded = Event()

    def load(self, position: int) -> Call[List[PeripheralDef]]:
        """Fetches the position's tree and replaces the catalog with it, unless another load or a clear came after
        (you switched DUT again meanwhile): then the late tree is dropped and the call resolves with the current."""
        self._generation += 1
        generation = self._generation

        def landed(peripherals: List[PeripheralDef]) -> List[PeripheralDef]:
            return self._set(peripherals) if generation == self._generation else self.peripherals
        return self._gateway.register_tree(position).map(landed)

    def _set(self, peripherals: List[PeripheralDef]) -> List[PeripheralDef]:
        self.peripherals = sorted(peripherals, key=lambda p: p.name)
        self._by_peripheral = {p.name: p for p in self.peripherals}
        self._registers = {r.full_name: r for p in self.peripherals for r in p.registers}
        self.loaded.emit()
        return self.peripherals

    def clear(self) -> None:
        self._generation += 1
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
        field = reg.field(field_name) if reg else None
        return (reg, field) if field else (None, None)

    def search(self, text: str) -> SearchResult:
        """The tree filter (core/search.py) with the current "show _NS/_S" preference."""
        return search_mod.search(self.peripherals, text, self._prefs.value.show_secure_peripherals)
