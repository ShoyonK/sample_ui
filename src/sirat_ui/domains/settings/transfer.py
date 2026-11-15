"""Export, import and clear user settings (req 2 File menu).

The export is one JSON file holding every settings file in its original format, so it can be
inspected by hand and imported on another station.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from pydantic import ValidationError

from sirat_ui import __version__
from sirat_ui.stores.json_store import JsonStore, UserStores
from sirat_ui.stores.schemas import CLEANERS, Problem, Report, SettingsBundle

FORMAT = "sirat-user-settings"
VERSION = 1


class SettingsTransfer:
    """Export, import and clear every settings file at once. reload_all makes the services re-read them."""

    def __init__(self, stores: UserStores, reload_all: Callable[[], None]) -> None:
        self._stores: Dict[str, JsonStore] = stores.by_name()
        self._reload_all = reload_all

    def export(self, path: Path) -> List[str]:
        """Writes the bundle. Returns the settings files it holds. Raises OSError when it can't be written."""
        bundle = {
            "format": FORMAT, "version": VERSION, "app_version": __version__,
            "exported": dt.datetime.now().isoformat(timespec="seconds"),
            "files": {name: store.load() for name, store in self._stores.items()},
        }
        Path(path).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        return list(bundle["files"])

    def import_(self, path: Path) -> Tuple[List[str], List[Problem]]:
        """Validates and writes every settings file in the bundle, then reloads.

        Returns (files imported, entries skipped). Raises ValueError when it isn't a settings export at all.
        """
        source = Path(path).name
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            bundle = SettingsBundle.model_validate(raw)
        except ValidationError:   # before ValueError: it's a subclass
            raise ValueError(f"{source} isn't a SiRAT settings export") from None
        except (OSError, ValueError) as exc:
            raise ValueError(f"Couldn't read {source}: {exc}") from None
        imported: List[str] = []
        report = Report(source)
        for name, content in bundle.files.items():
            if name not in self._stores:
                report.add(f"files.{name}", "not a SiRAT settings file; ignored")
                continue
            part = Report(source)
            self._stores[name].save(CLEANERS[name](content, part))
            report.problems += [Problem(source, f"files.{name}.{p.where}".rstrip("."), p.message)
                                for p in part.problems]
            imported.append(name)
        self._reload_all()
        return imported, report.problems

    def clear_all(self) -> None:
        """Resets every settings file to its defaults (req 2 "Clear All User Settings")."""
        for store in self._stores.values():
            store.reset()
        self._reload_all()
