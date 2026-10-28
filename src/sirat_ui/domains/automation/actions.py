"""Actions (req 13) and code generation (req 16). Actions run through automation.seq.run on the station."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional

from sirat_ui.core import codegen
from sirat_ui.core.actions import actions_to_json, migrate_actions
from sirat_ui.core.naming import unique_name
from sirat_ui.core.observable import Event
from sirat_ui.core.ops import WireError
from sirat_ui.core.wire_ops import action_ops
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.activities import ActivityTracker
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.port import AutomationPort
from sirat_ui.models.actions import Action
from sirat_ui.models.station import ActivityFinished, ActivityProgress
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState
from sirat_ui.stores.formats import read_custom_functions
from sirat_ui.stores.json_store import JsonStore


class ActionService:
    def __init__(self, store: JsonStore, gateway: AutomationPort, state: StationState, activities: ActivityTracker,
                 errors: ErrorPresenter, log: LogService, custom_functions: Optional[JsonStore] = None) -> None:
        self._store = store
        self._custom_functions = custom_functions
        self._gateway = gateway
        self._state = state
        self._activities = activities
        self._errors = errors
        self._log = log
        self.actions: "OrderedDict[str, Action]" = migrate_actions(store.load())
        self.changed = Event()
        self.run_finished = Event()  # (ok: bool)
        self.console = Event()       # (level, text): run output for the Actions console (req 13)

    def reload(self) -> None:
        self.actions = migrate_actions(self._store.load())
        self.changed.emit()

    def replace(self, raw: Dict[str, Any]) -> None:
        self.actions = migrate_actions(raw)
        self._save()

    def get(self, name: str) -> Optional[Action]:
        return self.actions.get(name)

    def unique_name(self, name: str) -> str:
        return unique_name(name, self.actions, "action")

    def add(self, name: str, ops: List[Dict[str, Any]], enabled: bool = True) -> Action:
        action = Action(self.unique_name(name), list(ops), enabled)
        self.actions[action.name] = action
        self._save()
        self._log.info(f"Saved action {action.name} ({len(ops)} ops)")
        return action

    def update(self, name: str, ops: List[Dict[str, Any]]) -> None:
        """Replaces an action's operations (req 13 Edit dialog)."""
        if name in self.actions:
            self.actions[name].operations = list(ops)
            self._save()
            self._log.info(f"Updated action {name}")

    def deselect_all(self) -> None:
        for action in self.actions.values():
            action.enabled = False
        self._save()

    def remove(self, name: str) -> None:
        self.actions.pop(name, None)
        self._save()

    def remove_all(self) -> None:
        self.actions.clear()
        self._save()

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name in self.actions:
            self.actions[name].enabled = enabled
            self._save()

    def move(self, name: str, delta: int) -> None:
        names = list(self.actions)
        if name not in names:
            return
        i = names.index(name)
        j = max(0, min(len(names) - 1, i + delta))
        names[i], names[j] = names[j], names[i]
        self.actions = OrderedDict((n, self.actions[n]) for n in names)
        self._save()

    def _functions(self) -> Dict[str, str]:
        return read_custom_functions(self._custom_functions.load()) if self._custom_functions else {}

    def wire_ops(self, name: str) -> List[Dict[str, Any]]:
        """The ops automation.seq.run gets for one action (core/wire_ops.py). Raises WireError."""
        return action_ops(self.actions[name], self.actions.get, self._functions())

    def ops_for(self, names: List[str]) -> List[Dict[str, Any]]:
        return [op for n in names if n in self.actions for op in self.wire_ops(n)]

    def run(self, names: List[str]) -> Call:
        label = ", ".join(names)
        try:
            ops = self.ops_for(names)
        except WireError as exc:
            error = ApiError(ErrorCode.INVALID_PARAMS, str(exc))
            self.console.emit("error", f"✗ {label}: {exc}")
            self._errors.present(error, f"Run {label}")
            return Call.failed(error)

        def started(activity_id: str) -> None:
            self._activities.follow(activity_id, self._progress, lambda event: self._finished(label, event))
            self._log.info(f"Running {label} ({len(ops)} ops)…")
            self.console.emit("info", f"▶ {label} ({len(ops)} ops)")

        def failed(error) -> None:
            self.console.emit("error", f"✗ {label}: {error.message}")
            self._errors.present(error, f"Run {label}")

        if not ops:
            self.console.emit("warning", "Nothing to run")
        return self._gateway.run_sequence(self._state.position, ops, True).then(started, failed)

    def run_enabled(self) -> Call:
        return self.run([a.name for a in self.actions.values() if a.enabled])

    def generate_code(self, names: List[str]) -> str:
        return codegen.generate([self.actions[n] for n in names if n in self.actions], self._functions())

    def _progress(self, event: ActivityProgress) -> None:
        self.console.emit("info", f"  {event.step}/{event.total}  {event.message}")

    def _finished(self, label: str, event: ActivityFinished) -> None:
        if event.ok:
            self._log.success(f"Finished {label}")
            self.console.emit("success", f"✓ {label} finished")
        elif event.error:
            self.console.emit("error", f"✗ {label}: {event.error.message}")
            self._errors.present(event.error, f"Run {label}")
        self.run_finished.emit(event.ok)

    def _save(self) -> None:
        self._store.save(actions_to_json(self.actions))
        self.changed.emit()

