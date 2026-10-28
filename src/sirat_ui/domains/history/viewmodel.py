"""Operation history panel (req 9): filter, Ctrl/Shift selection, re-run, actions, JSON export, code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core import codegen
from sirat_ui.domains.automation.recorder import ActionRecorder
from sirat_ui.domains.history.service import HistoryEntry, HistoryLog
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.models.dialogs import PromptField, PromptRequest
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.selection import RowSelection
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, clock_text, copy_to_clipboard, qprop


class HistoryViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, history: HistoryLog, catalog: RegisterCatalog, registers: RegisterService,
                 actions: ActionRecorder, interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._history = history
        self._catalog = catalog
        self._registers = registers
        self._actions = actions
        self._interactions = interactions
        self._model = DictListModel(["entryId", "time", "operation", "kind", "target", "valueText", "selected"], self)
        self._show_reads = True
        self._show_writes = True
        self._selection = RowSelection()
        history.changed.connect(self._rebuild)

    showReads = qprop(bool, "_show_reads", changed)
    showWrites = qprop(bool, "_show_writes", changed)

    @pyqtProperty(int, notify=changed)
    def selectedCount(self) -> int:  # noqa: N802
        return len(self._selection.selected)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    def _rebuild(self) -> None:
        rows = []
        for e in reversed(self._history.entries):
            if (e.operation == "READ" and not self._show_reads) or (e.operation == "WRITE" and not self._show_writes):
                continue
            if e.field is None:
                kind, value = e.operation.lower(), f"0x{e.value:08X}"
            else:  # req 9: field writes show the field value and the full register value
                kind = "field_write"
                value = f"0x{e.value:X}" + (f"  (register 0x{e.register_value:08X})" if e.register_value is not None else "")
            rows.append({"entryId": e.id, "time": clock_text(e.ts), "operation": e.operation, "kind": kind,
                         "target": e.target, "valueText": value, "selected": e.id in self._selection})
        self._selection.keep_only(e.id for e in self._history.entries)
        self._model.set_items(rows)
        self.changed.emit()

    # ---- filter and selection ------------------------------------------------------------------

    @pyqtSlot()
    def toggleReads(self) -> None:  # noqa: N802
        self._update(show_reads=not self._show_reads)
        self._rebuild()

    @pyqtSlot()
    def toggleWrites(self) -> None:  # noqa: N802
        self._update(show_writes=not self._show_writes)
        self._rebuild()

    @pyqtSlot(int, str)
    def select(self, row: int, mode: str) -> None:
        """mode: "single" (click), "toggle" (Ctrl+click), "range" (Shift+click)."""
        entry_id = self._model.get(row).get("entryId")
        if entry_id is not None:
            keys = [r["entryId"] for r in self._model.items]
            self._selection.select(keys, entry_id, mode)
            self._rebuild()

    def _selected_entries(self) -> List[HistoryEntry]:
        """The selection, oldest first; with nothing selected, the most recent entry."""
        entries = self._history.by_ids(self._selection.selected)
        return entries or self._history.entries[-1:]

    # ---- actions on the selection ----------------------------------------------------------------

    @pyqtSlot()
    def runSelected(self) -> None:  # noqa: N802
        for entry in self._selected_entries():
            reg = self._catalog.register(entry.register)
            if reg is None:
                continue
            if entry.operation == "READ":
                self._registers.read(reg)
            elif entry.field and (fdef := reg.field(entry.field)) is not None:
                self._registers.write_field(reg, fdef, entry.value)
            else:
                self._registers.write(reg, entry.value)

    @pyqtSlot()
    def createAction(self) -> None:  # noqa: N802
        ops = [e.as_op() for e in self._selected_entries() if e.operation == "WRITE"]
        if not ops:
            self._interactions.toast("error", "Select at least one write to create an action")
            return

        def answered(values) -> None:
            if values and values.get("name", "").strip():
                action = self._actions.add(values["name"], ops)
                self._selection.clear()
                self._rebuild()
                self._interactions.toast("success", f"Created action {action.name} ({len(ops)} ops)")

        self._interactions.prompt(PromptRequest("Create action from history", [
            PromptField("name", "Action name", "", "my_action")])).then(answered)

    @pyqtSlot()
    def saveSelected(self) -> None:  # noqa: N802
        """Req 9 context menu "Save Selected...": the selected entries as JSON in the req 9 format."""
        entries = self._history.by_ids(self._selection.selected)
        if not entries:
            self._interactions.toast("error", "Select the history entries to save")
            return
        records = []
        for e in entries:
            record: Dict[str, Any] = {"register": e.register, "operation": e.operation.lower(), "value": e.value}
            if e.operation == "WRITE":
                record["field"] = e.field
            records.append(record)

        def chosen(path) -> None:
            if not path:
                return
            try:
                Path(path).write_text(json.dumps(records, indent=2), encoding="utf-8")
                self._interactions.toast("success", f"Saved {len(records)} entries to {path}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save: {exc}")

        self._interactions.choose_save_file("Save history", "sirat_history.json", "JSON files (*.json)").then(chosen)

    @pyqtSlot()
    def generateCode(self) -> None:  # noqa: N802
        """Req 16: code from history. Uses the selection, or everything when nothing is selected."""
        entries = self._history.by_ids(self._selection.selected) or list(self._history.entries)
        if not entries:
            self._interactions.toast("error", "History is empty")
            return
        ops = [e.as_op() if e.operation == "WRITE" else {"type": "register_read", "register": e.register}
               for e in entries]
        self._interactions.show_code("Code from history", codegen.generate_from_ops(ops))

    @pyqtSlot()
    def copyAll(self) -> None:  # noqa: N802
        copy_to_clipboard(self._history.as_text())
        self._interactions.toast("info", "History copied")

    @pyqtSlot()
    def clear(self) -> None:
        self._selection.clear()
        self._history.clear()
