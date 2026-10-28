"""Sessions (req 34): Save Session dialog, Load Session browser (list, preview, Load, Delete), auto-save status."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.sessions.service import SessionService, count
from sirat_ui.shared.interactions import ConfirmRequest, InteractionService, PromptField, PromptRequest
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.shared.qt import pyqtProperty


def _when(iso: str) -> str:
    try:
        return dt.datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso or "—"


class SessionsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: SessionService, interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._interactions = interactions
        self._model = DictListModel(["name", "modified", "summary", "selected"], self)
        self._browser_open = False
        self._selected = ""
        self._preview: List[Dict[str, str]] = []
        self._autosave_text = ""
        service.changed.connect(self._rebuild)
        self._rebuild()

    browserOpen = qprop(bool, "_browser_open", changed)
    selectedName = qprop(str, "_selected", changed)
    preview = qprop("QVariantList", "_preview", changed)
    autosaveText = qprop(str, "_autosave_text", changed)

    @pyqtProperty(QObject, constant=True)
    def model(self) -> DictListModel:
        return self._model

    def _rebuild(self) -> None:
        sessions = self._service.list()
        names = [s.name for s in sessions]
        if self._selected not in names:
            self._selected = names[0] if names else ""
        self._model.set_items([{"name": s.name, "modified": _when(s.modified), "summary": s.summary,
                                "selected": s.name == self._selected} for s in sessions])
        last = self._service.last_autosave
        self._update(autosave_text=f"Auto-saved at {last:%H:%M}" if last else "Auto-saves every 5 minutes",
                     preview=self._preview_rows(self._selected))
        self.changed.emit()

    def _preview_rows(self, name: str) -> List[Dict[str, str]]:
        if not name:
            return []
        data: Dict[str, Any] = self._service.preview(name)
        favorites = data.get("favorites") or []
        actions = list((data.get("actions") or {}).keys())
        return [
            {"key": "Name", "value": str(data.get("session_name", name))},
            {"key": "Created", "value": _when(str(data.get("created", "")))},
            {"key": "Modified", "value": _when(str(data.get("modified", "")))},
            {"key": "Actions", "value": f"{len(actions)}: " + ", ".join(actions[:6]) + (" …" if len(actions) > 6 else "")
             if actions else "none"},
            {"key": "Favorites", "value": f"{len(favorites)}: " + ", ".join(favorites[:6]) + (" …" if len(favorites) > 6 else "")
             if favorites else "none"},
            {"key": "Notes", "value": str(len(data.get("field_notes") or {}))},
            {"key": "Formulas", "value": str(len(data.get("formulas") or []))},
            {"key": "History", "value": count(len(data.get("history") or []), "entry", "entries")},
            {"key": "Dumps", "value": str(len(data.get("dumps") or []))},
        ]

    # ---- Save Session ----------------------------------------------------------------------------

    @pyqtSlot()
    def saveSession(self) -> None:  # noqa: N802
        current = self._service.snapshot("preview")
        summary = (f"Saves {count(len(current['actions']), 'action')}, "
                   f"{count(len(current['favorites']), 'favorite')}, {count(len(current['field_notes']), 'note')}, "
                   f"{count(len(current['formulas']), 'formula')}, "
                   f"{count(len(current['dumps']), 'dump')} and "
                   f"{count(len(current['history']), 'history entry', 'history entries')}.")
        default = f"Session_{dt.datetime.now():%Y%m%d_%H%M%S}"

        def answered(values) -> None:
            name = (values or {}).get("name", "").strip()
            if not name:
                return
            if self._service.exists(name):
                request = ConfirmRequest(f"Replace session {name}?", "A session with this name exists. Saving replaces it.",
                                         confirm_text="Replace", tone="danger")
                self._interactions.confirm(request).then(lambda a: save(name) if a.accepted else None)
            else:
                save(name)

        def save(name: str) -> None:
            try:
                self._service.save(name)
                self._interactions.toast("success", f"Saved session {name}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save the session: {exc}")

        self._interactions.prompt(PromptRequest("Save session", [PromptField("name", "Session name", default)],
                                                message=summary, confirm_text="Save")).then(answered)

    # ---- Load Session browser --------------------------------------------------------------------

    @pyqtSlot()
    def openBrowser(self) -> None:  # noqa: N802
        self._update(browser_open=True)
        self._rebuild()

    @pyqtSlot()
    def closeBrowser(self) -> None:  # noqa: N802
        self._update(browser_open=False)

    @pyqtSlot(int)
    def select(self, row: int) -> None:
        name = self._model.get(row).get("name")
        if name:
            self._selected = name
            self._rebuild()

    @pyqtSlot()
    def loadSelected(self) -> None:  # noqa: N802
        name = self._selected
        if not name:
            return
        request = ConfirmRequest(f"Load session {name}?",
                                 "This replaces your current notes, formulas, actions, favorites and history "
                                 "with the ones saved in the session.", confirm_text="Load", tone="warning")

        def answered(answer) -> None:
            if not answer.accepted:
                return
            try:
                info = self._service.load(name)
            except ValueError as exc:
                self._interactions.toast("error", str(exc))
                return
            self._update(browser_open=False)
            skipped = self._service.last_problems
            if skipped:
                self._interactions.toast("warning", f"Loaded session {name}; skipped {len(skipped)} invalid "
                                                    "entries (details in the log)")
            else:
                self._interactions.toast("success", f"Loaded session {name}: {info.summary}")

        self._interactions.confirm(request).then(answered)

    @pyqtSlot()
    def deleteSelected(self) -> None:  # noqa: N802
        name = self._selected
        if not name:
            return
        request = ConfirmRequest(f"Delete session {name}?", "The session file is removed. You can't undo it.",
                                 confirm_text="Delete", tone="danger")
        self._interactions.confirm(request).then(lambda a: self._service.delete(name) if a.accepted else None)
