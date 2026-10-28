"""CustomFunctionService (req 15): the functions file, running a function in the shared session, and actions.

Functions persist in ~/.sirat_custom_functions.json as [{"name", "code"}]; edits save as you type. A run
uses the console's session, so variables carry over both ways, and the station stores the result as
result_<name> and last_dut_api_result there. One run at a time (req 15's re-entrance lock).
"""

from __future__ import annotations

import keyword
import time
from typing import Any, Dict, List, Optional

from sirat_ui.core.console import DEFAULT_FUNCTION_CODE, result_lines
from sirat_ui.core.observable import Event
from sirat_ui.domains.advanced.output import OutputLog
from sirat_ui.domains.advanced.session import PythonSession
from sirat_ui.domains.automation.recorder import ActionRecorder
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.port import AdvancedPort
from sirat_ui.models.actions import Action
from sirat_ui.models.station import ExecResult
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState
from sirat_ui.stores.json_store import JsonStore


def name_problem(name: str, taken: List[str]) -> str:
    """Names become result_<name> in the namespace, so they must be Python identifiers."""
    if not name:
        return "Give the function a name"
    if not name.isidentifier() or keyword.iskeyword(name):
        return "Use letters, digits and underscores, not starting with a digit (like read_rssi)"
    if name in taken:
        return f"There's already a function called {name}"
    return ""


class CustomFunctionService:
    def __init__(self, store: JsonStore, gateway: AdvancedPort, state: StationState, session: PythonSession,
                 actions: ActionRecorder, errors: ErrorPresenter) -> None:
        self._store = store
        self._gateway = gateway
        self._state = state
        self._session = session
        self._actions = actions
        self._errors = errors
        self.functions: List[Dict[str, str]] = []
        self.running = ""
        self.output = OutputLog()
        self.changed = Event()
        session.ended.connect(lambda reason: self.output.line("note", reason))
        self.reload()

    def reload(self) -> None:
        raw: Any = self._store.load()
        self.functions = [{"name": str(f["name"]), "code": str(f.get("code") or "")}
                          for f in (raw if isinstance(raw, list) else []) if isinstance(f, dict) and f.get("name")]
        self.changed.emit()

    @property
    def names(self) -> List[str]:
        return [f["name"] for f in self.functions]

    def code(self, name: str) -> Optional[str]:
        return next((f["code"] for f in self.functions if f["name"] == name), None)

    def _save(self) -> None:
        self._store.save([dict(f) for f in self.functions])
        self.changed.emit()

    def new_name(self) -> str:
        n = len(self.functions) + 1
        while f"function_{n}" in self.names:
            n += 1
        return f"function_{n}"

    def create(self, name: str) -> str:
        problem = name_problem(name, self.names)
        if not problem:
            self.functions.append({"name": name, "code": DEFAULT_FUNCTION_CODE if not self.functions else ""})
            self._save()
        return problem

    def rename(self, old: str, new: str) -> str:
        if new == old:
            return ""
        problem = name_problem(new, self.names)
        if not problem:
            for f in self.functions:
                if f["name"] == old:
                    f["name"] = new
            self._save()
        return problem

    def delete(self, name: str) -> None:
        self.functions = [f for f in self.functions if f["name"] != name]
        self._save()

    def set_code(self, name: str, code: str) -> None:
        for f in self.functions:
            if f["name"] == name and f["code"] != code:
                f["code"] = code
                self._save()

    def run(self, name: str) -> None:
        code = self.code(name)
        if code is None:
            return
        if self.running:
            self.output.line("note", f"{self.running} is still running; wait for it to finish")
            return
        self.running = name
        self.changed.emit()
        self.output.line("input", f"▶ {name}")
        started = time.monotonic()

        def finish() -> None:
            self.running = ""
            self.changed.emit()

        def done(result: ExecResult) -> None:
            finish()
            self.output.add(result_lines(result.stdout, result.stderr, result.result_text,
                                         result.error.text if result.error else None))
            if result.error is None:
                self.output.line("note", f"Finished in {(time.monotonic() - started) * 1000:.0f} ms"
                                         + ("" if result.result_text is None else f" · result_{name} is set"))

        def failed(error: ApiError) -> None:
            finish()
            self.output.line("error", self._errors.message_for(error))

        position = self._state.position
        self._session.with_session(
            lambda sid: self._gateway.custom_function(position, name, code, sid)).then(done, failed)

    def add_to_actions(self, name: str) -> Action:
        """Req 15 "Adding to Actions": {'type': 'custom_function', 'function_name': name}."""
        return self._actions.add(name, [{"type": "custom_function",
                                                                     "function_name": name}])
