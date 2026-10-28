"""Sessions (req 34): named snapshots of the user's working state, plus a 5-minute auto-save.

A session holds dumps, field notes, formulas, actions, favorites and history, in the req 34 file
format, one file per session in ~/.sirat/sessions/. Notes, formulas, actions and favorites already
persist in their own files, so loading a session writes them back there and reloads the services.
History is the one part that otherwise disappears on close (req 9), which is why the auto-save
restores it on the next launch. Dumps are the ones taken this run (req 12 keeps up to 50).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sirat_ui.core.observable import Event
from sirat_ui.stores.schemas import Problem, Report, clean_session
from sirat_ui.domains.annotations.service import AnnotationService, FavoritesService
from sirat_ui.domains.dumps.service import DumpService
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.history.service import HistoryLog
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.scheduler import Handle, Scheduler
from sirat_ui.core.actions import actions_to_json

AUTOSAVE_MS = 5 * 60 * 1000
AUTOSAVE_NAME = "autosave"


def count(n: int, singular: str, plural: str | None = None) -> str:
    """'1 note', '2 notes'."""
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


@dataclass
class SessionInfo:
    name: str
    path: Path
    created: str
    modified: str
    counts: Dict[str, int]

    @property
    def summary(self) -> str:
        c = self.counts
        return " · ".join([count(c["actions"], "action"), count(c["favorites"], "favorite"),
                           count(c["field_notes"], "note"), count(c["formulas"], "formula"),
                           count(c["history"], "history entry", "history entries")]
                          + ([count(c["dumps"], "dump")] if c["dumps"] else []))


def _counts(data: Dict[str, Any]) -> Dict[str, int]:
    return {key: len(data.get(key) or []) for key in ("dumps", "field_notes", "formulas", "actions",
                                                     "favorites", "history")}


def file_name(name: str) -> str:
    """Session names may contain anything; file names may not."""
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .") or "session"


class SessionService:
    def __init__(self, directory: Path, autosave_path: Path, annotations: AnnotationService,
                 favorites: FavoritesService, actions: ActionService, history: HistoryLog, dumps: DumpService,
                 log: LogService, scheduler: Scheduler, clock: Callable[[], dt.datetime] = dt.datetime.now) -> None:
        self.directory = Path(directory)
        self.autosave_path = Path(autosave_path)
        self._annotations = annotations
        self._favorites = favorites
        self._actions = actions
        self._history = history
        self._dumps = dumps
        self._log = log
        self._scheduler = scheduler
        self._clock = clock
        self._timer: Optional[Handle] = None
        self.last_autosave: Optional[dt.datetime] = None
        self.last_problems: List[Problem] = []  # what the last load skipped
        self.changed = Event()  # sessions list or auto-save status changed

    # ---- snapshot ---------------------------------------------------------------------------------

    def snapshot(self, name: str, created: Optional[str] = None) -> Dict[str, Any]:
        now = self._clock().isoformat(timespec="seconds")
        return {
            "session_name": name,
            "created": created or now,
            "modified": now,
            "dumps": self._dumps.to_records(),
            "field_notes": dict(self._annotations.notes),
            "formulas": [{"field": field, "formula": expr, "unit": unit}
                         for field, (expr, unit) in self._annotations.formulas.items()],
            "actions": actions_to_json(self._actions.actions),
            "favorites": list(self._favorites.names),
            "history": self._history.to_records(),
        }

    def apply(self, data: Dict[str, Any]) -> None:
        """Restores everything a session holds, writing it to the normal settings files."""
        formulas = {f["field"]: (f["formula"], f.get("unit", "")) for f in data.get("formulas") or []
                    if isinstance(f, dict) and f.get("field") and f.get("formula")}
        self._annotations.replace(dict(data.get("field_notes") or {}), formulas)
        self._actions.replace(data.get("actions") or {})
        self._favorites.replace([n for n in data.get("favorites") or [] if isinstance(n, str)])
        self._history.restore(data.get("history") or [])
        self._dumps.restore(data.get("dumps") or [])

    # ---- named sessions -------------------------------------------------------------------------------

    def path_for(self, name: str) -> Path:
        return self.directory / f"{file_name(name)}.json"

    def exists(self, name: str) -> bool:
        return self.path_for(name).exists()

    def list(self) -> List[SessionInfo]:
        sessions = []
        if self.directory.exists():
            for path in self.directory.glob("*.json"):
                data = self._read(path)
                if data is not None:
                    sessions.append(SessionInfo(str(data.get("session_name") or path.stem), path,
                                                str(data.get("created", "")), str(data.get("modified", "")),
                                                _counts(data)))
        return sorted(sessions, key=lambda s: s.modified, reverse=True)

    def save(self, name: str) -> SessionInfo:
        """Saves (or overwrites, keeping its created time) the named session."""
        path = self.path_for(name)
        existing = self._read(path) if path.exists() else None
        data = self.snapshot(name, existing.get("created") if existing else None)
        self._write(path, data)
        self._log.info(f"Saved session {name}")
        self.changed.emit()
        return SessionInfo(name, path, data["created"], data["modified"], _counts(data))

    def load(self, name: str) -> SessionInfo:
        """Validates the file (req 34 format), skipping invalid entries into last_problems, then applies it."""
        path = self.path_for(name)
        data = self._validated(path)
        if data is None:
            detail = f": {self.last_problems[0]}" if self.last_problems else ""
            raise ValueError(f"Couldn't read session {name}{detail}")
        for problem in self.last_problems:
            self._log.warning(f"Session {name}: skipped {problem}")
        self.apply(data)
        self._log.info(f"Loaded session {name}")
        return SessionInfo(name, path, str(data.get("created", "")), str(data.get("modified", "")), _counts(data))

    def delete(self, name: str) -> None:
        self.path_for(name).unlink(missing_ok=True)
        self._log.info(f"Deleted session {name}")
        self.changed.emit()

    def preview(self, name: str) -> Dict[str, Any]:
        return self._read(self.path_for(name)) or {}

    # ---- auto-save (req 34: every 5 minutes, restored on next launch) -----------------------------

    def start_autosave(self, interval_ms: int = AUTOSAVE_MS) -> None:
        self.stop_autosave()
        self._timer = self._scheduler.every(interval_ms, self.autosave)

    def stop_autosave(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def autosave(self) -> None:
        try:
            self._write(self.autosave_path, self.snapshot(AUTOSAVE_NAME))
        except OSError as exc:
            self._log.warning(f"Auto-save failed: {exc}")
            return
        self.last_autosave = self._clock()
        self.changed.emit()

    def restore_autosave(self) -> int:
        """Brings back the previous run's history. Returns how many entries were restored."""
        data = self._validated(self.autosave_path) if self.autosave_path.exists() else None
        if not data:
            return 0
        for problem in self.last_problems:
            self._log.warning(f"Auto-save: skipped {problem}")
        self._history.restore(data.get("history") or [])
        restored = len(self._history.entries)
        if restored:
            self._log.info(f"Restored {count(restored, 'history entry', 'history entries')} from the last session's auto-save")
        return restored

    # ---- files ----------------------------------------------------------------------------------------

    def _validated(self, path: Path) -> Optional[Dict[str, Any]]:
        report = Report(Path(path).name)
        raw = self._read(path)
        data = clean_session(raw, report) if raw is not None else None
        self.last_problems = report.problems if raw is not None else [Problem(report.source, "", "not readable JSON")]
        return data

    def _read(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _write(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(path)
