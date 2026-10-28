"""Sequences (req 14): ordered lists of action names, run as one batch on the station.

Execution rules from req 14: disabled actions are skipped, actions that no longer exist are skipped
with a warning, and the action currently executing is highlighted. Steps are therefore one per
*action*; progress events (one per operation) are mapped back to the action that owns the operation.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from sirat_ui.core.actions import main_kind, summarize_ops
from sirat_ui.core.observable import Event
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.models import ActivityFinished, ActivityProgress
from sirat_ui.gateway.port import StationGateway
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.app_state import AppState
from sirat_ui.stores.formats import SequenceRecord, read_sequences, write_sequences
from sirat_ui.stores.json_store import JsonStore

RUNNABLE = "pending"


@dataclass
class Step:
    """One action in a sequence."""
    title: str                # action name
    kind: str                 # main operation kind, for the colored chip
    detail: str               # "4 ops · load_phy, rf_switch", or why it's skipped
    state: str = RUNNABLE     # pending | running | done | failed | skipped | missing
    first_op: int = -1        # index of this action's first operation in the batch
    op_count: int = 0
    started: Optional[float] = None
    duration: Optional[float] = None

    @property
    def runnable(self) -> bool:
        return self.op_count > 0

    def owns(self, op_index: int) -> bool:
        return self.runnable and self.first_op <= op_index < self.first_op + self.op_count


@dataclass
class SequenceRun:
    name: str
    steps: List[Step] = field(default_factory=list)
    activity_id: Optional[str] = None
    running: bool = False
    message: str = ""
    ok: Optional[bool] = None


class SequenceService:
    def __init__(self, store: JsonStore, actions: ActionService, gateway: StationGateway, state: AppState,
                 errors: ErrorPresenter, log: LogService, clock: Callable[[], float] = time.time) -> None:
        self._store = store
        self._actions = actions
        self._gateway = gateway
        self._state = state
        self._errors = errors
        self._log = log
        self._clock = clock
        self._records = read_sequences(store.load())
        # name -> action names; descriptions are kept in _records and written back untouched
        self.sequences: "OrderedDict[str, List[str]]" = OrderedDict(
            (name, record.action_names) for name, record in self._records.items())
        self.last_run: Dict[str, float] = {}
        self.current: Optional[SequenceRun] = None
        self.changed = Event()
        self.progress = Event()
        self.console = Event()  # (level, text): run output for the Sequences console (req 14)
        gateway.events.connect(self._on_event)

    # ---- editing ---------------------------------------------------------------------------------

    def reload(self) -> None:
        self._records = read_sequences(self._store.load())
        self.sequences = OrderedDict((name, record.action_names) for name, record in self._records.items())
        self.changed.emit()

    def description(self, name: str) -> str:
        record = self._records.get(name)
        return record.description if record else ""

    def create(self, name: str, action_names: List[str]) -> str:
        base, candidate, n = name.strip() or "sequence", name.strip() or "sequence", 2
        while candidate in self.sequences:
            candidate, n = f"{base}_{n}", n + 1
        self.sequences[candidate] = list(action_names)
        self._save()
        return candidate

    def rename(self, old: str, new: str) -> str:
        new = new.strip()
        if old not in self.sequences or not new or new == old:
            return old
        if new in self.sequences:
            raise ValueError(f"A sequence named {new} already exists")
        self.sequences = OrderedDict((new if n == old else n, steps) for n, steps in self.sequences.items())
        if old in self._records:
            self._records[new] = self._records.pop(old)
        self._save()
        return new

    def add_steps(self, name: str, action_names: List[str]) -> None:
        """Appends actions to a sequence (req 14: from the Actions panel or the Add action picker)."""
        if name in self.sequences:
            self.sequences[name].extend(action_names)
            self._save()

    def to_action(self, name: str) -> str:
        """Req 14 "Add to Actions Panel": a sequence operation that runs this sequence's actions."""
        op = {"type": "sequence", "sequence_name": name, "action_names": list(self.sequences.get(name, []))}
        return self._actions.add(name, [op]).name

    def delete(self, name: str) -> None:
        self.sequences.pop(name, None)
        self._save()

    def move_step(self, name: str, index: int, delta: int) -> None:
        steps = self.sequences.get(name)
        if not steps or not 0 <= index < len(steps):
            return
        j = max(0, min(len(steps) - 1, index + delta))
        steps[index], steps[j] = steps[j], steps[index]
        self._save()

    def remove_step(self, name: str, index: int) -> None:
        steps = self.sequences.get(name)
        if steps and 0 <= index < len(steps):
            steps.pop(index)
            self._save()

    # ---- running ---------------------------------------------------------------------------------

    def plan(self, name: str) -> Tuple[List[Step], List[Dict[str, Any]]]:
        """Steps (one per action) and the operations to send, with req 14's skip rules applied."""
        steps: List[Step] = []
        ops: List[Dict[str, Any]] = []
        for action_name in self.sequences.get(name, []):
            action = self._actions.get(action_name)
            if action is None:
                steps.append(Step(action_name, "missing", "Action not found · skipped", "missing"))
            elif not action.enabled:
                steps.append(Step(action_name, main_kind(action.operations),
                                  "Disabled · skipped", "skipped"))
            else:
                steps.append(Step(action_name, main_kind(action.operations), summarize_ops(action.operations),
                                  first_op=len(ops), op_count=len(action.operations)))
                ops.extend(action.operations)
        return steps, ops

    def preview(self, name: str) -> List[Step]:
        return self.plan(name)[0]

    def run(self, name: str) -> Call:
        steps, ops = self.plan(name)
        self.console.emit("info", f"▶ Sequence {name}")
        for step in steps:
            if step.state == "missing":
                self._log.warning(f"Sequence {name}: action '{step.title}' not found, skipped")
                self.console.emit("warning", f"  ! {step.title}: not found, skipped")
            elif step.state == "skipped":
                self._log.info(f"Sequence {name}: action '{step.title}' is disabled, skipped")
                self.console.emit("info", f"  – {step.title}: disabled, skipped")
        if not ops:
            self.console.emit("error", "✗ No enabled actions to run")
            error = ApiError(ErrorCode.INVALID_PARAMS, "No enabled actions to run")
            self._errors.present(error, f"Sequence {name}")
            return Call.failed(error)

        self.current = SequenceRun(name, steps, running=True, message="Starting…")
        self.progress.emit()

        def started(activity_id: str) -> None:
            if self.current:
                self.current.activity_id = activity_id

        def failed(error: ApiError) -> None:
            if self.current:
                self.current.running = False
                self.current.message = "Couldn't start"
            self._errors.present(error, f"Run {name}")
            self.progress.emit()

        return self._gateway.run_sequence(self._state.position, ops, True).then(started, failed)

    def abort(self) -> None:
        if self.current and self.current.activity_id and self.current.running:
            self.current.message = "Aborting…"
            self._gateway.abort_sequence(self.current.activity_id)
            self.progress.emit()

    def generate_code(self, name: str) -> str:
        enabled = [n for n in self.sequences.get(name, []) if (a := self._actions.get(n)) and a.enabled]
        return self._actions.generate_code(enabled)

    def _on_event(self, event: object) -> None:
        run = self.current
        if run is None or getattr(event, "activity_id", None) != run.activity_id:
            return
        now = self._clock()
        if isinstance(event, ActivityProgress):
            op_index = event.step - 1
            for step in run.steps:
                if step.owns(op_index):
                    if step.state != "running":
                        step.state, step.started = "running", now
                        self.console.emit("info", f"  → {step.title}")
                    run.message = f"{step.title}: {event.message}…"
                elif step.runnable and step.first_op + step.op_count <= op_index and step.state == "running":
                    step.state, step.duration = "done", now - (step.started or now)
        elif isinstance(event, ActivityFinished):
            for step in run.steps:
                if step.state == "running":
                    step.state = "done" if event.ok else "failed"
                    step.duration = now - (step.started or now)
            run.running, run.ok = False, event.ok
            ran = sum(1 for s in run.steps if s.state == "done")
            skipped = sum(1 for s in run.steps if s.state in ("skipped", "missing"))
            summary = f"{ran} action(s) done" + (f", {skipped} skipped" if skipped else "")
            run.message = f"Finished · {summary}" if event.ok else (event.error.message if event.error else "Failed")
            self.last_run[run.name] = now
            if not event.ok and event.error:
                self.console.emit("error", f"✗ {run.name}: {event.error.message}")
                self._errors.present(event.error, f"Sequence {run.name}")
            else:
                self.console.emit("success", f"✓ {run.name} finished · {summary}")
                self._log.success(f"Sequence {run.name} finished · {summary}")
        self.progress.emit()

    def _save(self) -> None:
        self._records = OrderedDict(
            (name, SequenceRecord(list(steps), self._records.get(name, SequenceRecord()).description))
            for name, steps in self.sequences.items())
        self._store.save(write_sequences(self._records))
        self.changed.emit()
