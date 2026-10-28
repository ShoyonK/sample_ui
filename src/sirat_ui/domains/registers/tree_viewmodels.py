"""Peripheral tree (req §4, §6) and favorites column (req §8)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from sirat_ui.core.formatting import NOT_READ, format_value
from sirat_ui.core.registers import PeripheralDef, RegisterDef
from sirat_ui.core.search import SearchResult
from sirat_ui.domains.annotations.service import FavoritesService
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.registers.read_all import ReadAllService
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

SEARCH_DEBOUNCE_MS = 300
TREE_ROLES = ["key", "kind", "name", "fullName", "address", "valueText", "access", "depth", "expanded",
              "selected", "hasChildren"]


class PeripheralTreeViewModel(BaseViewModel):
    changed = pyqtSignal()
    searchFocusRequested = pyqtSignal()

    def __init__(self, state: AppState, catalog: RegisterCatalog, registers: RegisterService,
                 read_all: ReadAllService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._catalog = catalog
        self._registers = registers
        self._read_all = read_all
        self._model = DictListModel(TREE_ROLES, self)
        self._search_text = ""
        self._pending_text = ""
        self._result: Optional[SearchResult] = None
        self._expanded: Set[str] = set()
        self._peripheral_count = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SEARCH_DEBOUNCE_MS)
        self._timer.timeout.connect(self.flushSearch)
        catalog.loaded.connect(self._on_loaded)
        registers.value_changed.connect(lambda *_: self._rebuild())
        state.selection_changed.connect(self._on_selection)
        state.preferences_changed.connect(lambda _: self._on_loaded())

    searchText = qprop(str, "_search_text", changed)
    peripheralCount = qprop(int, "_peripheral_count", changed)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    # ---- search ------------------------------------------------------------------------------

    @pyqtSlot(str)
    def setSearchText(self, text: str) -> None:  # noqa: N802
        self._pending_text = text
        self._timer.start()

    @pyqtSlot()
    def requestSearchFocus(self) -> None:  # noqa: N802
        self.searchFocusRequested.emit()

    @pyqtSlot()
    def flushSearch(self) -> None:  # noqa: N802
        self._timer.stop()
        self._update(search_text=self._pending_text)
        self._result = self._catalog.search(self._search_text)
        if self._result.is_empty_query:
            self._expanded.clear()
        if self._result.auto_select:
            reg = self._catalog.register(self._result.auto_select)
            if reg:
                self._state.select(reg, by_user=False)
        self._rebuild()

    def _on_selection(self, selection, by_user: bool) -> None:
        """Reveal a register selected from elsewhere (favorites, search, scripts) by expanding its peripheral."""
        if isinstance(selection, RegisterDef):
            self._expanded.add(selection.peripheral)
        self._rebuild()

    def _on_loaded(self) -> None:
        self._result = self._catalog.search(self._search_text)
        self._update(peripheral_count=len(self._result.peripherals))
        self._rebuild()

    # ---- rows --------------------------------------------------------------------------------

    def _rebuild(self) -> None:
        result = self._result or self._catalog.search(self._search_text)
        fmt = self._state.preferences.format
        selected = self._state.selection
        rows: List[Dict[str, Any]] = []
        for name in result.peripherals:
            periph = self._catalog.peripheral(name)
            if periph is None:
                continue
            expanded = name in self._expanded or name in result.expanded
            rows.append(self._peripheral_row(periph, expanded, selected is periph))
            if not expanded:
                continue
            allowed = result.registers.get(name)
            for reg in periph.registers:
                if allowed is None or reg.name in allowed:
                    value = self._registers.cached(reg.full_name)
                    rows.append({
                        "key": reg.full_name, "kind": "register", "name": reg.name, "fullName": reg.full_name,
                        "address": f"0x{reg.address:08X}", "access": reg.access.value, "depth": 1,
                        "valueText": NOT_READ if value is None else format_value(value, fmt, reg.width),
                        "expanded": False, "selected": selected is reg, "hasChildren": False,
                    })
        self._model.set_items(rows)

    @staticmethod
    def _peripheral_row(periph: PeripheralDef, expanded: bool, selected: bool) -> Dict[str, Any]:
        return {"key": periph.name, "kind": "peripheral", "name": periph.name, "fullName": periph.name,
                "address": f"0x{periph.base_address:08X}", "access": "", "depth": 0, "valueText": "",
                "expanded": expanded, "selected": selected, "hasChildren": bool(periph.registers)}

    def _row_target(self, row: int):
        item = self._model.get(row)
        if not item:
            return None
        if item["kind"] == "peripheral":
            return self._catalog.peripheral(item["name"])
        return self._catalog.register(item["fullName"])

    @pyqtSlot(int)
    def activate(self, row: int) -> None:
        target = self._row_target(row)
        if isinstance(target, PeripheralDef):
            # First tap selects and expands; tapping the selected peripheral again toggles it.
            if self._state.selection is target:
                self.toggleExpanded(row)
            else:
                self._expanded.add(target.name)
                self._state.select(target, by_user=True)
        elif isinstance(target, RegisterDef):
            self._state.select(target, by_user=True)

    @pyqtSlot(int)
    def toggleExpanded(self, row: int) -> None:  # noqa: N802
        target = self._row_target(row)
        if isinstance(target, PeripheralDef):
            if target.name in self._expanded or (self._result and target.name in self._result.expanded):
                self._expanded.discard(target.name)
                if self._result:
                    self._result.expanded.discard(target.name)
            else:
                self._expanded.add(target.name)
            self._rebuild()

    @pyqtSlot()
    def collapseAll(self) -> None:  # noqa: N802
        self._expanded.clear()
        if self._result:
            self._result.expanded.clear()
        self._rebuild()

    @pyqtSlot(int)
    def readAll(self, row: int) -> None:  # noqa: N802
        target = self._row_target(row)
        if isinstance(target, PeripheralDef):
            self._read_all.start(target)


class FavoritesViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, state: AppState, catalog: RegisterCatalog, favorites: FavoritesService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._catalog = catalog
        self._favorites = favorites
        self._model = DictListModel(["fullName", "address"], self)
        self._visible = False
        favorites.changed.connect(self._rebuild)
        catalog.loaded.connect(self._rebuild)
        self._rebuild()

    visible = qprop(bool, "_visible", changed)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    def _rebuild(self) -> None:
        rows = []
        for name in sorted(self._favorites.names):  # req 8: "list sorted alphabetically"
            reg = self._catalog.register(name)
            rows.append({"fullName": name, "address": f"0x{reg.address:08X}" if reg else ""})
        self._model.set_items(rows)
        self._update(visible=bool(rows))

    @pyqtSlot(int)
    def activate(self, row: int) -> None:
        reg = self._catalog.register(self._model.get(row).get("fullName", ""))
        if reg:
            self._state.select(reg, by_user=True)

    @pyqtSlot(int)
    def remove(self, row: int) -> None:
        name = self._model.get(row).get("fullName")
        if name:
            self._favorites.remove(name)
