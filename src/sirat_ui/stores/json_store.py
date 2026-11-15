"""JsonStore plus the set of stores SiRAT auto-loads at startup (req §1, same file names).

File contents follow the original formats; see stores/formats.py. Every load goes through the file's pydantic
schema (stores/schemas): invalid entries are skipped and listed in `problems`, and the original file is copied
to <name>.bak first, so the next save can't lose what was skipped.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sirat_ui.stores.schemas import CLEANERS, Cleaner, Problem, Report
from sirat_ui.stores.schemas.files import BlePacketModel, HardwareConfigModel, SignalGeneratorModel

log = logging.getLogger("SiRAT.stores")


def write_json(path: Path, data: Any) -> None:
    """Writes JSON atomically: to <name>.tmp first, then renamed over the file, so a crash can't half-write it.

    Raises:
        OSError: The folder or file can't be written. The temporary file is removed first.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


class JsonStore:
    """One JSON settings file: load() validates it through its cleaner, save() writes it atomically.

    `default` is what a missing or unreadable file loads as; it's deep-copied each time, so callers may change it.
    """

    def __init__(self, path: Path, default: Any, cleaner: Optional[Cleaner] = None) -> None:
        self.path = Path(path)
        self._default = default
        self._cleaner = cleaner
        self.problems: List[Problem] = []  # from the last load()
        # Called instead of raising when a save fails (disk full, no permission, file locked); the app sets it
        self.on_save_error: Optional[Callable[["JsonStore", OSError], None]] = None

    def load(self) -> Any:
        """The file's contents, cleaned. Skipped entries go to `problems`, and the original is kept as .bak."""
        self.problems = []
        if not self.path.exists():
            return copy.deepcopy(self._default)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.problems = [Problem(self.path.name, "", f"couldn't read the file ({exc}); using defaults")]
            self._backup()
            log.warning("Couldn't read %s (%s); using defaults", self.path, exc)
            return copy.deepcopy(self._default)
        if self._cleaner is None:
            return raw
        report = Report(self.path.name)
        clean = self._cleaner(raw, report)
        if report:
            self.problems = report.problems
            self._backup()
            for problem in report.problems:
                log.warning("Skipped invalid setting: %s", problem)
        return clean

    def _backup(self) -> None:
        """Keeps the file as it was before anything skipped from it can be overwritten by a save."""
        backup = self.path.with_name(self.path.name + ".bak")
        try:
            backup.write_bytes(self.path.read_bytes())
        except OSError as exc:
            log.warning("Couldn't back up %s (%s)", self.path, exc)

    def save(self, data: Any) -> bool:
        """Writes atomically. Returns False if it failed and on_save_error was told; raises if nobody listens."""
        try:
            write_json(self.path, data)
        except OSError as exc:
            if self.on_save_error is None:
                raise
            self.on_save_error(self, exc)
            return False
        return True

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def reset(self) -> None:
        """Writes the default contents (req 2 "Clear All User Settings")."""
        self.save(copy.deepcopy(self._default))


@dataclass
class UserStores:
    """Every settings file SiRAT loads at startup. Field names are the code's; by_name() gives the export names."""
    favorites: JsonStore
    actions: JsonStore
    watch_list: JsonStore
    data_logger: JsonStore
    custom_functions: JsonStore
    sequences: JsonStore
    formulas: JsonStore
    notes: JsonStore
    preferences: JsonStore
    hardware_config: JsonStore
    signal_generator: JsonStore
    ble_packet: JsonStore
    memory_viewer: JsonStore

    @classmethod
    def in_home(cls, home: Path) -> "UserStores":
        home = Path(home)
        sirat = home / ".sirat"
        return cls(
            favorites=JsonStore(home / ".sirat_favorites.json", {"favorites": []}, CLEANERS["favorites"]),
            actions=JsonStore(home / ".sirat_actions.json", {}, CLEANERS["actions"]),
            watch_list=JsonStore(home / ".sirat_watch_list.json", {"watched_fields": [], "refresh_rate": 1.0},
                                 CLEANERS["watch_list"]),
            data_logger=JsonStore(home / ".sirat_data_logger.json", {"tracked_fields": [], "sample_rate": 1.0},
                                  CLEANERS["data_logger"]),
            custom_functions=JsonStore(home / ".sirat_custom_functions.json", [], CLEANERS["custom_functions"]),
            sequences=JsonStore(home / ".sirat_sequences.json", {}, CLEANERS["sequences"]),
            formulas=JsonStore(sirat / "field_formulas.json", {}, CLEANERS["field_formulas"]),
            notes=JsonStore(sirat / "field_notes.json", {}, CLEANERS["field_notes"]),
            preferences=JsonStore(sirat / "preferences.json", {}, CLEANERS["preferences"]),
            # the schema models hold the defaults, so the files and the validation agree on them
            hardware_config=JsonStore(sirat / "hardware_config.json", HardwareConfigModel().model_dump(mode="json"),
                                      CLEANERS["hardware_config"]),
            signal_generator=JsonStore(sirat / "signal_generator.json",
                                       SignalGeneratorModel().model_dump(mode="json"), CLEANERS["signal_generator"]),
            ble_packet=JsonStore(sirat / "ble_packet.json", BlePacketModel().model_dump(mode="json"),
                                 CLEANERS["ble_packet"]),
            memory_viewer=JsonStore(sirat / "memory_viewer.json", {"last_address": "0x20000000"},
                                    CLEANERS["memory_viewer"]),
        )

    def all(self) -> List[JsonStore]:
        return [getattr(self, f.name) for f in fields(self)]

    def by_name(self) -> Dict[str, JsonStore]:
        """Every store by its settings-export name (the CLEANERS keys); differs from the field name for two."""
        names = {"formulas": "field_formulas", "notes": "field_notes"}
        return {names.get(f.name, f.name): getattr(self, f.name) for f in fields(self)}

    def problems(self) -> List[Problem]:
        """What the last load of every file skipped."""
        return [p for store in self.all() for p in store.problems]
