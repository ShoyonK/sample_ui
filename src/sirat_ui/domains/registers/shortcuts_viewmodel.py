"""The register page's "send to" commands: favorite, watch, logger, formula, save to Actions, read the peripheral.

Each hands the open register or a field (by full name) to another feature. Kept apart from the detail panel,
which shows and edits the register itself.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSlot

from sirat_ui.domains.annotations.formula_viewmodel import FormulaEditorViewModel
from sirat_ui.domains.annotations.service import FavoritesService
from sirat_ui.domains.automation.recorder import ActionRecorder
from sirat_ui.domains.monitoring.logger import DataLoggerService
from sirat_ui.domains.monitoring.watch import WatchService
from sirat_ui.domains.registers.read_all import ReadAllService
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.models.dialogs import PromptField, PromptRequest
from sirat_ui.models.registers import PeripheralDef
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.state.selection import SelectionState


class RegisterShortcutsViewModel(QObject):
    def __init__(self, selection: SelectionState, registers: RegisterService, favorites: FavoritesService,
                 watch: WatchService, logger: DataLoggerService, actions: ActionRecorder,
                 formula_editor: FormulaEditorViewModel, read_all: ReadAllService, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._selection = selection
        self._registers = registers
        self._favorites = favorites
        self._watch = watch
        self._logger = logger
        self._actions = actions
        self._formula_editor = formula_editor
        self._read_all = read_all
        self._interactions = interactions

    @pyqtSlot()
    def toggleFavorite(self) -> None:  # noqa: N802
        reg = self._selection.register
        if reg:
            self._favorites.toggle(reg.full_name)

    @pyqtSlot(str)
    def addToWatch(self, field: str) -> None:  # noqa: N802
        added = self._watch.add(field)
        self._interactions.toast("info", f"{'Added' if added else 'Already watching'} {field}")

    @pyqtSlot(str)
    def addToLogger(self, field: str) -> None:  # noqa: N802
        added = self._logger.track(field)
        self._interactions.toast("info", f"{'Logging' if added else 'Already logging'} {field}")

    @pyqtSlot(str)
    def editFormula(self, field: str) -> None:  # noqa: N802
        self._formula_editor.open_for(field)

    @pyqtSlot()
    def readPeripheral(self) -> None:  # noqa: N802
        if isinstance(self._selection.current, PeripheralDef):
            self._read_all.start(self._selection.current)

    @pyqtSlot()
    def saveToActions(self) -> None:  # noqa: N802
        reg = self._selection.register
        value = self._registers.cached(reg.full_name) if reg else None
        if reg is None or value is None:
            self._interactions.toast("error", "Read the register before saving it to actions")
            return

        def answered(values) -> None:
            if values and values.get("name", "").strip():
                action = self._actions.add(values["name"], [{"register": reg.full_name, "value": value}])
                self._interactions.toast("success", f"Saved action {action.name}")

        self._interactions.prompt(PromptRequest("Save register to actions", [
            PromptField("name", "Action name", reg.name.lower(), "lpmode_on")])).then(answered)
