"""Advanced page, Custom functions tab (req 15): the list, the highlighted editor, Run and Add to Actions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.console import FUNCTION_PLACEHOLDER
from sirat_ui.domains.advanced.advanced_viewmodel import OutputModel
from sirat_ui.domains.advanced.functions import CustomFunctionService
from sirat_ui.models.dialogs import ConfirmRequest, PromptField, PromptRequest
from sirat_ui.shared.highlighter import HighlighterHost
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, qprop
from sirat_ui.state.station import StationState


class CustomFunctionsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: CustomFunctionService, state: StationState, interactions: InteractionService,
                 highlighters: HighlighterHost, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._interactions = interactions
        self._highlighters = highlighters
        self._selected = service.names[0] if service.names else ""
        self._output = OutputModel(service.output, self)
        service.changed.connect(self._on_service)
        state.changed.connect(self.changed.emit)

    def _on_service(self) -> None:
        if self._selected not in self._service.names:
            self._selected = self._service.names[0] if self._service.names else ""
        self.changed.emit()

    @pyqtProperty(QObject, constant=True)
    def output(self) -> QObject:
        return self._output

    @pyqtProperty("QStringList", notify=changed)
    def functions(self) -> List[str]:
        return self._service.names

    selectedName = qprop(str, "_selected", changed)

    @pyqtProperty(str, constant=True)
    def placeholder(self) -> str:
        return FUNCTION_PLACEHOLDER

    @pyqtProperty(bool, notify=changed)
    def running(self) -> bool:
        return bool(self._service.running)

    @pyqtProperty(bool, notify=changed)
    def hasSelection(self) -> bool:  # noqa: N802
        return bool(self._selected)

    @pyqtProperty(int, notify=changed)
    def selectedIndex(self) -> int:  # noqa: N802
        names = self._service.names
        return names.index(self._selected) if self._selected in names else -1

    @pyqtProperty(str, notify=changed)
    def code(self) -> str:
        return self._service.code(self._selected) or ""

    @pyqtProperty(bool, notify=changed)
    def canRun(self) -> bool:  # noqa: N802
        return bool(self._selected) and self._state.connected and not self._service.running

    @pyqtProperty(str, notify=changed)
    def runHint(self) -> str:  # noqa: N802
        if not self._selected:
            return ""
        if self._service.running:
            return f"Running {self._service.running}…"
        if not self._state.connected:
            return "Connect a DUT to run functions"
        return "Shares variables with the console · Ctrl+Enter runs"

    @pyqtSlot(int)
    def select(self, index: int) -> None:
        names = self._service.names
        if 0 <= index < len(names):
            self._update(selected=names[index])

    @pyqtSlot(str)
    def setCode(self, text: str) -> None:  # noqa: N802
        if self._selected:
            self._service.set_code(self._selected, text)

    @pyqtSlot(QObject, bool)
    def attachHighlighter(self, document: QObject, dark: bool) -> None:  # noqa: N802
        self._highlighters.attach(document, dark)

    @pyqtSlot()
    def newFunction(self) -> None:  # noqa: N802
        def answered(values: Optional[Dict[str, Any]]) -> None:
            if values is None:
                return
            name = str(values.get("name", "")).strip()
            problem = self._service.create(name)
            if problem:
                self._interactions.toast("error", problem)
            else:
                self._update(selected=name)

        self._interactions.prompt(PromptRequest(
            "New function", [PromptField("name", "Name", self._service.new_name(), "read_rssi")],
            "Its result is stored as result_<name>, so use a Python name.", confirm_text="Create")).then(answered)

    @pyqtSlot()
    def renameFunction(self) -> None:  # noqa: N802
        old = self._selected

        def answered(values: Optional[Dict[str, Any]]) -> None:
            if values is None:
                return
            name = str(values.get("name", "")).strip()
            problem = self._service.rename(old, name)
            if problem:
                self._interactions.toast("error", problem)
            else:
                self._update(selected=name)

        if old:
            self._interactions.prompt(PromptRequest(f"Rename {old}", [PromptField("name", "New name", old)],
                                                    "Actions that call the old name won't find it.",
                                                    confirm_text="Rename")).then(answered)

    @pyqtSlot()
    def deleteFunction(self) -> None:  # noqa: N802
        name = self._selected
        if not name:
            return
        request = ConfirmRequest(f"Delete {name}", "The function's code is removed from "
                                 "~/.sirat_custom_functions.json. Actions that call it will fail.",
                                 confirm_text="Delete", tone="danger")
        self._interactions.confirm(request).then(lambda a: self._service.delete(name) if a.accepted else None)

    @pyqtSlot()
    def run(self) -> None:
        if self.canRun:
            self._service.run(self._selected)

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if self._selected:
            action = self._service.add_to_actions(self._selected)
            self._interactions.toast("success", f"Added {action.name} to Actions")
