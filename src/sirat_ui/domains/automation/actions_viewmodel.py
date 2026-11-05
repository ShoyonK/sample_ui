"""Actions panel and page (req 13, 16): list, run, reorder, delete, add to sequence, code, console."""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.actions import main_kind, summarize_ops
from sirat_ui.domains.automation.action_editor import ActionEditorViewModel
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.automation.sequences import SequenceService
from sirat_ui.models.dialogs import ConfirmRequest, PromptField, PromptRequest
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.selection import RowSelection
from sirat_ui.shared.viewmodel import BaseViewModel, ConsoleModel, DictListModel, qprop
from sirat_ui.state.station import StationState

NEW_SEQUENCE = "New sequence…"


def show_code(interactions: InteractionService, title: str, code: str) -> None:
    interactions.show_code(title, code)


class ActionsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, actions: ActionService, sequences: SequenceService, editor: ActionEditorViewModel,
                 state: StationState, interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._actions = actions
        self._sequences = sequences
        self._editor = editor
        self._state = state
        self._interactions = interactions
        self._model = DictListModel(["name", "enabled", "opsText", "kind", "selected"], self)
        self._console = ConsoleModel(self)
        self._selection = RowSelection()   # by name; Ctrl and Shift add to it
        self._current = ""                 # the selected action when exactly one is selected
        self._selected_count = 0
        self._checked_count = 0
        self._total = 0
        self._can_run = state.can("automation.seq.run")
        actions.changed.connect(self._rebuild)
        actions.console.connect(self._console.append)
        state.changed.connect(lambda: self._update(can_run=state.can("automation.seq.run")))
        self._rebuild()

    canRun = qprop(bool, "_can_run", changed)
    currentName = qprop(str, "_current", changed)
    selectedCount = qprop(int, "_selected_count", changed)
    checkedCount = qprop(int, "_checked_count", changed)
    total = qprop(int, "_total", changed)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    @pyqtProperty(QObject, constant=True)
    def console(self) -> ConsoleModel:
        return self._console

    def _rebuild(self) -> None:
        self._selection.keep_only(self._actions.actions)
        selected = self._selected_names()
        self._current = selected[0] if len(selected) == 1 else ""
        self._model.set_items([{"name": a.name, "enabled": a.enabled, "opsText": summarize_ops(a.operations),
                               "kind": main_kind(a.operations), "selected": a.name in self._selection}
                               for a in self._actions.actions.values()])
        self._update(checked_count=len(self._checked()), total=len(self._actions.actions),
                     selected_count=len(selected))
        self.changed.emit()

    def _name(self, row: int) -> Optional[str]:
        return self._model.get(row).get("name")

    def _checked(self) -> List[str]:
        return [a.name for a in self._actions.actions.values() if a.enabled]

    def _selected_names(self) -> List[str]:
        return [name for name in self._actions.actions if name in self._selection]

    def _require_current(self) -> Optional[str]:
        if self._current in self._actions.actions:
            return self._current
        self._interactions.toast("error", "Select an action first")
        return None

    # ---- selection and checkboxes ----------------------------------------------------------------

    @pyqtSlot(int)
    def select(self, row: int) -> None:
        self.selectRow(row, "single")

    @pyqtSlot(int, str)
    def selectRow(self, row: int, mode: str) -> None:  # noqa: N802
        """mode: "single" (click), "toggle" (Ctrl+click), "range" (Shift+click)."""
        name = self._name(row)
        if name:
            self._selection.select(list(self._actions.actions), name, mode)
            self._rebuild()

    def select_name(self, name: str) -> None:
        if name in self._actions.actions:
            self._selection.select(list(self._actions.actions), name)
            self._rebuild()

    @pyqtSlot(int)
    def toggleEnabled(self, row: int) -> None:  # noqa: N802
        name = self._name(row)
        if name:
            self._actions.set_enabled(name, not self._actions.actions[name].enabled)

    @pyqtSlot()
    def deselectAll(self) -> None:  # noqa: N802
        self._actions.deselect_all()

    @pyqtSlot(bool)
    def setAllChecked(self, checked: bool) -> None:  # noqa: N802
        """The checkbox above the list: checks every action, or unchecks them all."""
        self._actions.set_all_enabled(checked)

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
    def removeSelected(self) -> None:  # noqa: N802
        """Deletes every selected action; asks first when it's more than one."""
        names = self._selected_names()
        if not names:
            self._interactions.toast("error", "Select an action first")
            return
        if len(names) == 1:
            self._actions.remove(names[0])
            return
        shown = ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else "")
        request = ConfirmRequest(f"Delete {len(names)} actions", f"{shown}. You can't undo it.",
                                 confirm_text="Delete", tone="danger")
        self._interactions.confirm(request).then(lambda a: self._actions.remove_many(names) if a.accepted else None)

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
