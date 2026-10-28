"""Actions panel and page (req 13, 16): list, run, reorder, delete, add to sequence, code, console."""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.actions import main_kind, summarize_ops
from sirat_ui.domains.automation.action_editor import ActionEditorViewModel
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.automation.sequences import SequenceService
from sirat_ui.shared.interactions import ConfirmRequest, InteractionService, PromptField, PromptRequest
from sirat_ui.shared.viewmodel import BaseViewModel, ConsoleModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

NEW_SEQUENCE = "New sequence…"


def show_code(interactions: InteractionService, title: str, code: str) -> None:
    interactions.show_code(title, code)


class ActionsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, actions: ActionService, sequences: SequenceService, editor: ActionEditorViewModel,
                 state: AppState, interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._actions = actions
        self._sequences = sequences
        self._editor = editor
        self._state = state
        self._interactions = interactions
        self._model = DictListModel(["name", "enabled", "opsText", "kind", "current"], self)
        self._console = ConsoleModel(self)
        self._current = ""
        self._can_run = state.can("automation.seq.run")
        actions.changed.connect(self._rebuild)
        actions.console.connect(self._console.append)
        state.changed.connect(lambda: self._update(can_run=state.can("automation.seq.run")))
        self._rebuild()

    canRun = qprop(bool, "_can_run", changed)
    currentName = qprop(str, "_current", changed)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    @pyqtProperty(QObject, constant=True)
    def console(self) -> ConsoleModel:
        return self._console

    def _rebuild(self) -> None:
        if self._current not in self._actions.actions:
            self._current = ""
        self._model.set_items([{"name": a.name, "enabled": a.enabled, "opsText": summarize_ops(a.operations),
                                "kind": main_kind(a.operations), "current": a.name == self._current}
                               for a in self._actions.actions.values()])
        self.changed.emit()

    def _name(self, row: int) -> Optional[str]:
        return self._model.get(row).get("name")

    def _checked(self) -> List[str]:
        return [a.name for a in self._actions.actions.values() if a.enabled]

    def _require_current(self) -> Optional[str]:
        if self._current in self._actions.actions:
            return self._current
        self._interactions.toast("error", "Select an action first")
        return None

    # ---- selection and checkboxes ----------------------------------------------------------------

    @pyqtSlot(int)
    def select(self, row: int) -> None:
        self._current = self._name(row) or ""
        self._rebuild()

    def select_name(self, name: str) -> None:
        if name in self._actions.actions:
            self._current = name
            self._rebuild()

    @pyqtSlot(int)
    def toggleEnabled(self, row: int) -> None:  # noqa: N802
        name = self._name(row)
        if name:
            self._actions.set_enabled(name, not self._actions.actions[name].enabled)

    @pyqtSlot()
    def deselectAll(self) -> None:  # noqa: N802
        self._actions.deselect_all()

    # ---- run ----------------------------------------------------------------------------------------

    @pyqtSlot()
    def runCurrent(self) -> None:  # noqa: N802
        name = self._require_current()
        if name:
            self._actions.run([name])

    @pyqtSlot()
    def runSelected(self) -> None:  # noqa: N802
        if not self._checked():
            self._interactions.toast("error", "Check at least one action to run")
            return
        self._actions.run_enabled()

    # ---- view / edit (req 13 dialogs) ---------------------------------------------------------

    @pyqtSlot()
    def viewCurrent(self) -> None:  # noqa: N802
        name = self._require_current()
        if name:
            self._editor.open_view(name)

    @pyqtSlot()
    def editCurrent(self) -> None:  # noqa: N802
        name = self._require_current()
        if name:
            self._editor.open_edit(name)

    # ---- order and delete ---------------------------------------------------------------------

    @pyqtSlot(int)
    def moveCurrent(self, delta: int) -> None:  # noqa: N802
        if self._current in self._actions.actions:
            self._actions.move(self._current, delta)

    @pyqtSlot()
    def removeCurrent(self) -> None:  # noqa: N802
        name = self._require_current()
        if name:
            self._actions.remove(name)

    @pyqtSlot()
    def removeAll(self) -> None:  # noqa: N802
        request = ConfirmRequest("Delete all actions", "This removes every saved action. You can't undo it.",
                                 confirm_text="Delete all", tone="danger")
        self._interactions.confirm(request).then(lambda a: self._actions.remove_all() if a.accepted else None)

    # ---- sequences (req 14 "Add to Sequence...") --------------------------------------------------

    @pyqtSlot()
    def addCheckedToSequence(self) -> None:  # noqa: N802
        checked = self._checked()
        if not checked:
            self._interactions.toast("error", "Check the actions to add first")
            return
        choices = [NEW_SEQUENCE] + list(self._sequences.sequences)

        def answered(values) -> None:
            if not values:
                return
            target = values.get("sequence", NEW_SEQUENCE)
            if target == NEW_SEQUENCE:
                if not values.get("name", "").strip():
                    self._interactions.toast("error", "Enter a name for the new sequence")
                    return
                target = self._sequences.create(values["name"], checked)
            else:
                self._sequences.add_steps(target, checked)
            self._interactions.toast("success", f"Added {len(checked)} action(s) to {target}")

        self._interactions.prompt(PromptRequest(
            "Add checked actions to a sequence",
            [PromptField("sequence", "Sequence", NEW_SEQUENCE, options=choices),
             PromptField("name", "New sequence name (only for a new sequence)", "", "ble_bringup")],
            message=f"{len(checked)} checked action(s), added in list order.", confirm_text="Add",
        )).then(answered)

    # ---- code (req 16) ---------------------------------------------------------------------------

    @pyqtSlot()
    def generateCode(self) -> None:  # noqa: N802
        names = self._checked() or list(self._actions.actions)
        show_code(self._interactions, "Generated code", self._actions.generate_code(names))
