"""DutControlService (req 22): the DUT control API tree, invoking a method, and recording it as an action.

The tree is fetched once per connected position and dropped on disconnect.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sibench_ui.core.dut_control import action_name, call_text, hint_for, method_op
from sibench_ui.core.observable import Event
from sibench_ui.domains.advanced.output import OutputLog
from sibench_ui.domains.automation.recorder import ActionRecorder
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.port import AdvancedPort
from sibench_ui.models.actions import Action
from sibench_ui.models.station import ApiMethod, ApiTree, InvokeRes
from sibench_ui.shared.error_presenter import ErrorPresenter
from sibench_ui.state.station import StationState


class DutControlService:
    """The DUT control API explorer: the method tree per connected position, invoking, and Add to Actions."""

    def __init__(self, gateway: AdvancedPort, state: StationState, actions: ActionRecorder,
                 errors: ErrorPresenter) -> None:
        self._gateway = gateway
        self._state = state
        self._actions = actions
        self._errors = errors
        self.tree: Optional[ApiTree] = None
        self.tree_position = 0
        self.loading = False
        self.load_error = ""
        self.running = ""
        self.output = OutputLog()
        self.changed = Event()
        state.changed.connect(self._on_state)

    def _on_state(self) -> None:
        if self.tree_position and (self.tree_position != self._state.position or not self._state.connected):
            self.tree, self.tree_position, self.load_error = None, 0, ""
            self.changed.emit()

    def load(self, force: bool = False) -> None:
        """Fetches the tree once per connected position. A failed load waits for Reload (force=True)."""
        if self.loading or not self._state.connected:
            return
        if not force and (self.tree is not None or self.load_error):   # a failed load waits for Reload
            return
        self.loading, self.load_error = True, ""
        self.changed.emit()
        position = self._state.position

        def done(tree: ApiTree) -> None:
            self.loading, self.tree, self.tree_position = False, tree, position
            self.changed.emit()

        def failed(error: ApiError) -> None:
            self.loading, self.load_error = False, self._errors.message_for(error)
            self.tree_position = position
            self.changed.emit()

        self._gateway.dut_control_describe(position).then(done, failed)

    def method(self, path: str) -> Optional[ApiMethod]:
        packages = self.tree.packages if self.tree else ()
        methods = (m for package in packages for module in package.modules for m in module.methods)
        return next((m for m in methods if m.path == path), None)

    def invoke(self, path: str, kwargs: Dict[str, Any]) -> None:
        """Calls the method on the selected DUT and writes the call and its result (or advice) to the output."""
        if self.running:
            return
        self.running = path
        self.changed.emit()
        self.output.line("input", f"▶ {call_text(path, kwargs)}")

        def done(res: InvokeRes) -> None:
            self.running = ""
            self.changed.emit()
            self.output.line("result", f"✓ Result ({res.result_type}): {res.result_text}")

        def failed(error: ApiError) -> None:
            self.running = ""
            self.changed.emit()
            self._report_failure(error)

        self._gateway.dut_control_invoke(self._state.position, path, [], kwargs).then(done, failed)

    def _report_failure(self, error: ApiError) -> None:
        """The error, plus for a DUT exception a hint for its cause and the traceback."""
        hardware = error.code == ErrorCode.HARDWARE_ERROR    # the DUT's own exception says more here
        self.output.line("error", f"✗ {error.message if hardware else self._errors.message_for(error)}")
        if not hardware:
            return
        hint = hint_for(str(error.data.get("cause", "")))
        if hint:
            self.output.line("hint", hint)
        trace = str(error.data.get("traceback") or "")
        if "\n" in trace:          # a one-line traceback only repeats the error
            self.output.line("note", trace)

    def add_to_actions(self, path: str, kwargs: Dict[str, Any]) -> Action:
        return self._actions.add(action_name(path), [method_op(path, kwargs)])
