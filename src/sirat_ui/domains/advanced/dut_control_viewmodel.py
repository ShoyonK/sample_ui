"""Advanced page, DUT control tab (req 22): the API tree, method details, the parameter form, Execute."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.dut_control import FORMAT_HINT, build_kwargs, default_text
from sirat_ui.domains.advanced.advanced_viewmodel import OutputModel
from sirat_ui.domains.advanced.dut_control import DutControlService
from sirat_ui.models.station import ApiMethod
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.station import StationState


class DutControlViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: DutControlService, state: StationState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._interactions = interactions
        self._filter = ""
        self._expanded: Set[str] = set()
        self._selected = ""
        self._values: Dict[str, str] = {}
        self._problems: List[str] = []
        self._rows = DictListModel(["key", "kind", "label", "depth", "expanded", "selected", "count"], self)
        self._params = DictListModel(["name", "annotation", "value", "isBool", "required", "placeholder"], self)
        self._output = OutputModel(service.output, self)
        service.changed.connect(self._refresh)
        state.changed.connect(self.changed.emit)
        self._refresh()

    @pyqtProperty(QObject, constant=True)
    def rows(self) -> QObject:
        return self._rows

    @pyqtProperty(QObject, constant=True)
    def params(self) -> QObject:
        return self._params

    @pyqtProperty(QObject, constant=True)
    def output(self) -> QObject:
        return self._output

    filterText = qprop(str, "_filter", changed)

    @pyqtProperty(str, constant=True)
    def formatHint(self) -> str:  # noqa: N802
        return FORMAT_HINT

    selectedPath = qprop(str, "_selected", changed)

    @pyqtProperty(bool, notify=changed)
    def running(self) -> bool:
        return bool(self._service.running)

    @pyqtProperty(bool, notify=changed)
    def loading(self) -> bool:
        return self._service.loading

    @pyqtProperty(str, notify=changed)
    def problemText(self) -> str:  # noqa: N802
        return " · ".join(self._problems)

    def _method(self) -> Optional[ApiMethod]:
        return self._service.method(self._selected) if self._selected else None

    @pyqtProperty(str, notify=changed)
    def signature(self) -> str:
        m = self._method()
        return m.signature if m else ""

    @pyqtProperty(str, notify=changed)
    def doc(self) -> str:
        m = self._method()
        return (m.doc or "No docstring.") if m else ""

    @pyqtProperty(str, notify=changed)
    def treeText(self) -> str:  # noqa: N802
        """Why the tree is empty, if it is."""
        if not self._state.connected:
            return "Connect a DUT to browse its control API"
        if self._service.loading:
            return "Loading the API…"
        if self._service.load_error:
            return self._service.load_error
        if self._service.tree is not None and self._rows.count == 0:
            return f"Nothing matches “{self._filter}”"
        return ""

    @pyqtProperty(bool, notify=changed)
    def canExecute(self) -> bool:  # noqa: N802
        return bool(self._method()) and self._state.connected and not self._service.running and not self._problems

    # ---- tree -----------------------------------------------------------------------------------------------

    def _refresh(self) -> None:
        tree = self._service.tree
        if self._selected and self._service.method(self._selected) is None:
            self._selected = ""
            self._load_params()
        rows: List[Dict[str, Any]] = []
        needle = self._filter.lower()
        for package in (tree.packages if tree else ()):
            package_rows: List[Dict[str, Any]] = []
            for module in package.modules:
                methods = [m for m in module.methods if not needle or needle in m.path.lower()]
                if not methods:
                    continue
                open_ = bool(needle) or module.path in self._expanded
                package_rows.append(self._row(module.path, "module", module.name, 1, open_, len(methods)))
                if open_:
                    package_rows += [self._row(m.path, "method", m.name, 2, False, 0) for m in methods]
            if package_rows:
                open_ = bool(needle) or package.name in self._expanded
                rows.append(self._row(package.name, "package", package.name, 0, open_, len(package.modules)))
                if open_:
                    rows += package_rows
        self._rows.set_items(rows)
        self.changed.emit()

    def _row(self, key: str, kind: str, label: str, depth: int, expanded: bool, count: int) -> Dict[str, Any]:
        return {"key": key, "kind": kind, "label": label, "depth": depth, "expanded": expanded,
                "selected": key == self._selected, "count": count}

    @pyqtSlot()
    def load(self) -> None:
        """Called when the tab shows; fetches the tree once per connected DUT."""
        self._service.load()

    @pyqtSlot()
    def reload(self) -> None:
        self._service.load(force=True)

    @pyqtSlot(str)
    def setFilter(self, text: str) -> None:  # noqa: N802
        self._filter = text.strip()
        self._refresh()

    @pyqtSlot(int)
    def activate(self, row: int) -> None:
        item = self._rows.get(row)
        if not item:
            return
        if item["kind"] == "method":
            self._selected = item["key"]
            self._load_params()
        else:
            self._expanded ^= {item["key"]}
        self._refresh()

    @pyqtSlot()
    def collapseAll(self) -> None:  # noqa: N802
        self._expanded.clear()
        self._filter = ""
        self._refresh()

    # ---- parameters ----------------------------------------------------------------------------------------

    def _param_dicts(self) -> List[Dict[str, Any]]:
        m = self._method()
        return [{"name": p.name, "annotation": p.annotation, "default_repr": p.default_repr,
                 "required": p.required} for p in (m.params if m else ())]

    def _load_params(self) -> None:
        params = self._param_dicts()
        self._values = {p["name"]: default_text(p["default_repr"]) for p in params}
        self._check()

    def _check(self) -> None:
        params = self._param_dicts()
        _, self._problems = build_kwargs(params, self._values)
        self._params.set_items([
            {"name": p["name"], "annotation": p["annotation"] or "any", "value": self._values.get(p["name"], ""),
             "isBool": p["annotation"] == "bool", "required": p["required"],
             "placeholder": p["annotation"] + (" (required)" if p["required"] else "")} for p in params])

    @pyqtSlot(str, str)
    def setParam(self, name: str, value: str) -> None:  # noqa: N802
        if name in self._values:
            self._values[name] = value
            self._check()
            self.changed.emit()

    def _kwargs(self) -> Dict[str, Any]:
        kwargs, _ = build_kwargs(self._param_dicts(), self._values)
        return kwargs

    @pyqtSlot()
    def execute(self) -> None:
        if self.canExecute:
            self._service.invoke(self._selected, self._kwargs())

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if self._method() and not self._problems:
            action = self._service.add_to_actions(self._selected, self._kwargs())
            self._interactions.toast("success", f"Added {action.name} to Actions")
