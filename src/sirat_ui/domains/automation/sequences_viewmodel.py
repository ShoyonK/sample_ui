"""Sequences page (req 14): list, per-action steps, editing, run/abort, console, code."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.automation.actions_viewmodel import show_code
from sirat_ui.domains.automation.sequences import SequenceService
from sirat_ui.models.dialogs import ConfirmRequest, PromptField, PromptRequest
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, ConsoleModel, DictListModel, qprop
from sirat_ui.state.station import StationState


class SequencesViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, sequences: SequenceService, actions: ActionService, state: StationState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._sequences = sequences
        self._actions = actions
        self._state = state
        self._interactions = interactions
        self._list = DictListModel(["name", "detail", "selected"], self)
        self._steps = DictListModel(["num", "title", "kind", "detail", "state", "durationText", "selected"], self)
        self._console = ConsoleModel(self)
        self._selected = next(iter(sequences.sequences), "")
        self._selected_step = -1
        self._running = False
        self._progress = 0.0
        self._status_text = ""
        self._message = ""
        self._can_run = state.can("automation.seq.run")
        sequences.changed.connect(self._rebuild)
        sequences.progress.connect(self._rebuild)
        sequences.console.connect(self._console.append)
        actions.changed.connect(self._rebuild)
        state.changed.connect(lambda: self._update(can_run=state.can("automation.seq.run")))
        self._rebuild()

    selectedName = qprop(str, "_selected", changed)
    selectedStep = qprop(int, "_selected_step", changed)
    running = qprop(bool, "_running", changed)
    progress = qprop(float, "_progress", changed)
    statusText = qprop(str, "_status_text", changed)
    message = qprop(str, "_message", changed)
    canRun = qprop(bool, "_can_run", changed)

    @pyqtProperty(QObject, constant=True)
    def sequenceList(self) -> DictListModel:  # noqa: N802
        return self._list

    @pyqtProperty(QObject, constant=True)
    def steps(self) -> DictListModel:
        return self._steps

    @pyqtProperty(QObject, constant=True)
    def console(self) -> ConsoleModel:
        return self._console

    # ---- rows ------------------------------------------------------------------------------------

    def _rebuild(self) -> None:
        if self._selected not in self._sequences.sequences:
            self._selected = next(iter(self._sequences.sequences), "")
        rows = []
        for name, action_names in self._sequences.sequences.items():
            detail = f"{len(action_names)} action" + ("" if len(action_names) == 1 else "s")
            if self._sequences.description(name):
                detail += " · " + self._sequences.description(name)
            if name in self._sequences.last_run:
                detail += " · last run " + time.strftime("%I:%M %p", time.localtime(self._sequences.last_run[name]))
            rows.append({"name": name, "detail": detail, "selected": name == self._selected})
        self._list.set_items(rows)

        current_run = self._sequences.current
        run = current_run if current_run is not None and current_run.name == self._selected else None
        showing_run = run is not None
        steps = run.steps if run is not None else self._sequences.preview(self._selected)
        if self._selected_step >= len(steps):
            self._selected_step = len(steps) - 1
        self._steps.set_items([self._step_row(i, s) for i, s in enumerate(steps)])
        runnable = [s for s in steps if s.runnable]
        done = sum(1 for s in runnable if s.state in ("done", "failed"))
        current = next((i + 1 for i, s in enumerate(runnable) if s.state == "running"), done)
        if run is not None and run.running:
            status = f"Running · action {current} of {len(runnable)}"
        elif run is not None and run.ok is not None:
            status = "Finished" if run.ok else "Failed"
        else:
            skipped = len(steps) - len(runnable)
            status = f"Ready · {len(runnable)} to run" + (f", {skipped} skipped" if skipped else "")
        self._update(selected=self._selected, running=run is not None and run.running,
                     progress=(done / len(runnable)) if runnable and showing_run else 0.0,
                     status_text=status, message=run.message if run is not None else "")
        self.changed.emit()

    def _step_row(self, i: int, step) -> Dict[str, Any]:
        duration = f"{step.duration:.1f} s" if step.duration is not None else ("…" if step.state == "running" else "—")
        return {"num": f"{i + 1:02d}", "title": step.title, "kind": step.kind, "detail": step.detail,
                "state": step.state, "durationText": duration, "selected": i == self._selected_step}

    # ---- selection -----------------------------------------------------------------------------

    @pyqtSlot(int)
    def select(self, row: int) -> None:
        self._selected = self._list.get(row).get("name", self._selected)
        self._selected_step = -1
        self._rebuild()

    def select_name(self, name: str) -> None:
        if name in self._sequences.sequences:
            self._selected = name
            self._selected_step = -1
            self._rebuild()

    @pyqtSlot(int)
    def selectStep(self, row: int) -> None:  # noqa: N802
        self._selected_step = row
        self._rebuild()

    # ---- run -------------------------------------------------------------------------------------

    @pyqtSlot()
    def run(self) -> None:
        if self._selected:
            self._sequences.run(self._selected)

    @pyqtSlot()
    def abort(self) -> None:
        self._sequences.abort()

    # ---- sequence editing ------------------------------------------------------------------------

    @pyqtSlot()
    def newSequence(self) -> None:  # noqa: N802
        def answered(values) -> None:
            if values and values.get("name", "").strip():
                self._selected = self._sequences.create(values["name"], [])  # req 14: starts empty
                self._rebuild()

        self._interactions.prompt(PromptRequest(
            "New sequence", [PromptField("name", "Sequence name", "", "tx_sweep")],
            message="It starts empty. Add actions with Add action, or from the Actions page.")).then(answered)

    @pyqtSlot()
    def renameSequence(self) -> None:  # noqa: N802
        old = self._selected
        if not old:
            return

        def answered(values) -> None:
            if not values:
                return
            try:
                self._selected = self._sequences.rename(old, values.get("name", ""))
            except ValueError as exc:
                self._interactions.toast("error", str(exc))
            self._rebuild()

        self._interactions.prompt(PromptRequest(f"Rename {old}", [PromptField("name", "New name", old)],
                                                confirm_text="Rename")).then(answered)

    @pyqtSlot()
    def deleteSequence(self) -> None:  # noqa: N802
        name = self._selected
        request = ConfirmRequest(f"Delete {name}", "The actions it uses are kept.", confirm_text="Delete", tone="danger")
        self._interactions.confirm(request).then(lambda a: self._sequences.delete(name) if a.accepted else None)

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if self._selected:
            name = self._sequences.to_action(self._selected)
            self._interactions.toast("success", f"Added sequence {self._selected} to Actions as {name}")

    # ---- step editing ----------------------------------------------------------------------------

    @pyqtSlot()
    def addAction(self) -> None:  # noqa: N802
        names = list(self._actions.actions)
        if not self._selected or not names:
            self._interactions.toast("error", "Create a sequence and at least one action first")
            return

        def answered(values) -> None:
            if values and values.get("action") in self._actions.actions:
                self._sequences.add_steps(self._selected, [values["action"]])

        self._interactions.prompt(PromptRequest(f"Add action to {self._selected}",
                                                [PromptField("action", "Action", names[0], options=names)],
                                                confirm_text="Add")).then(answered)

    @pyqtSlot()
    def removeSelectedStep(self) -> None:  # noqa: N802
        if self._selected_step >= 0:
            self._sequences.remove_step(self._selected, self._selected_step)

    @pyqtSlot(int)
    def moveSelectedStep(self, delta: int) -> None:  # noqa: N802
        steps = self._sequences.sequences.get(self._selected, [])
        if 0 <= self._selected_step < len(steps):
            target = max(0, min(len(steps) - 1, self._selected_step + delta))
            self._sequences.move_step(self._selected, self._selected_step, delta)
            self._selected_step = target
            self._rebuild()

    # ---- code ------------------------------------------------------------------------------------

    @pyqtSlot()
    def generateCode(self) -> None:  # noqa: N802
        show_code(self._interactions, f"Code for {self._selected}", self._sequences.generate_code(self._selected))
