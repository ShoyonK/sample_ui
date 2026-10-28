"""View and Edit dialogs for one action (req 13).

View: every operation, read-only; code carried by an operation (custom functions, signal generator,
GFSK) is shown with Python highlighting. Edit: register and field write values are editable; other
operation types are listed as information.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.actions import CODE_KINDS, EDITABLE_KINDS, describe_op, op_kind
from sirat_ui.core.formatting import ValueFormat, parse_value
from sirat_ui.core.highlight import highlight_python
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

EDIT_ROLES = ["index", "kind", "description", "editable", "valueText", "info"]


def _value_text(op: Dict[str, Any]) -> str:
    value = int(op.get("value", 0))
    return f"0x{value:08X}" if op_kind(op) == "register_write" else f"0x{value:X}"


class ActionEditorViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, actions: ActionService, catalog: RegisterCatalog, state: AppState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._actions = actions
        self._catalog = catalog
        self._state = state
        self._interactions = interactions
        self._view_open = False
        self._view_title = ""
        self._view_html = ""
        self._edit_open = False
        self._edit_title = ""
        self._edit_name: Optional[str] = None
        self._pending: Dict[int, str] = {}
        self._rows = DictListModel(EDIT_ROLES, self)

    viewOpen = qprop(bool, "_view_open", changed)
    viewTitle = qprop(str, "_view_title", changed)
    viewHtml = qprop(str, "_view_html", changed)
    editOpen = qprop(bool, "_edit_open", changed)
    editTitle = qprop(str, "_edit_title", changed)

    @pyqtProperty(QObject, constant=True)
    def editRows(self) -> DictListModel:  # noqa: N802
        return self._rows

    # ---- View ------------------------------------------------------------------------------------

    def open_view(self, name: str) -> None:
        action = self._actions.get(name)
        if action is None:
            return
        dark = self._state.preferences.dark_mode
        parts: List[str] = []
        for i, op in enumerate(action.operations, 1):
            kind = op_kind(op)
            parts.append(f"<p style='margin:10px 0 4px 0;'><b>{i}. {html.escape(kind.replace('_', ' '))}</b>"
                         f" &nbsp; {html.escape(describe_op(op))}</p>")
            code = op.get("code")
            if kind in CODE_KINDS and code:
                parts.append(highlight_python(str(code), dark))
        if not parts:
            parts.append("<p>This action has no operations.</p>")
        state = "checked" if action.enabled else "not checked"
        header = f"<p style='color:gray;'>{len(action.operations)} operation(s) · {state}</p>"
        self._update(view_open=True, view_title=f"View action: {name}", view_html=header + "".join(parts))

    @pyqtSlot()
    def closeView(self) -> None:  # noqa: N802
        self._update(view_open=False)

    # ---- Edit ------------------------------------------------------------------------------------

    def open_edit(self, name: str) -> None:
        action = self._actions.get(name)
        if action is None:
            return
        rows = []
        for i, op in enumerate(action.operations):
            kind = op_kind(op)
            editable = kind in EDITABLE_KINDS
            target = op["register"] + (f".{op['field']}" if kind == "field_write" else "") if editable else ""
            rows.append({
                "index": i, "kind": kind, "description": target if editable else describe_op(op),
                "editable": editable, "valueText": _value_text(op) if editable else "",
                "info": "" if editable else "Not editable here. Re-create it from its tool page.",
            })
        self._edit_name = name
        self._pending = {}
        self._rows.set_items(rows)
        self._update(edit_open=True, edit_title=f"Edit action: {name}")

    @pyqtSlot(int, str)
    def setEditValue(self, row: int, text: str) -> None:  # noqa: N802
        self._pending[row] = text

    @pyqtSlot()
    def saveEdit(self) -> None:  # noqa: N802
        action = self._actions.get(self._edit_name or "")
        if action is None:
            self.cancelEdit()
            return
        ops = [dict(op) for op in action.operations]
        for row, text in self._pending.items():
            op = ops[row]
            try:
                value = parse_value(text, ValueFormat.HEX)
            except ValueError as exc:
                self._interactions.toast("error", f"Operation {row + 1}: {exc}")
                return
            limit = self._max_value(op)
            if limit is not None and value > limit:
                self._interactions.toast("error", f"Operation {row + 1}: 0x{value:X} is out of range (max 0x{limit:X})")
                return
            op["value"] = value
        self._actions.update(action.name, ops)
        self._interactions.toast("success", f"Saved {action.name}")
        self.cancelEdit()

    @pyqtSlot()
    def cancelEdit(self) -> None:  # noqa: N802
        self._edit_name = None
        self._pending = {}
        self._update(edit_open=False)

    def _max_value(self, op: Dict[str, Any]) -> Optional[int]:
        reg = self._catalog.register(op.get("register", ""))
        if reg is None:
            return None  # registers aren't known until a DUT is connected; the station still range-checks
        if op_kind(op) == "field_write":
            field = reg.field(op.get("field", ""))
            return field.max_value if field else None
        return reg.max_value
