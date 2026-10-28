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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from sirat_ui.stores.schemas import CLEANERS, Cleaner, Problem, Report

log = logging.getLogger("SiRAT.stores")


class JsonStore:
    def __init__(self, path: Path, default: Any, cleaner: Optional[Cleaner] = None) -> None:
        self.path = Path(path)
        self._default = default
        self._cleaner = cleaner
        self.problems: List[Problem] = []  # from the last load()

    def load(self) -> Any:
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

    def save(self, data: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def reset(self) -> None:
        """Writes the default contents (req 2 "Clear All User Settings")."""
        self.save(copy.deepcopy(self._default))


@dataclass
class UserStores:
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
            hardware_config=JsonStore(sirat / "hardware_config.json",
                                      {"rpc_host": "localhost", "rpc_port": 10001, "rpc_timeout": 5,
                                       "dut_position": 1, "rpc_override": False}, CLEANERS["hardware_config"]),
            signal_generator=JsonStore(sirat / "signal_generator.json",
                                       {"sg_type": "PacketSrw", "input_config_name": "BLE_1M", "frequency_mhz": 2440.0,
                                        "power_dbm": 0.0, "overrides": {}}, CLEANERS["signal_generator"]),
            ble_packet=JsonStore(sirat / "ble_packet.json",
                                 {"access_address": "0x8E89BED6", "crc_init": "0x555555", "whitening_init": 37,
                                  "preamble": "0xAA"}, CLEANERS["ble_packet"]),
            memory_viewer=JsonStore(sirat / "memory_viewer.json", {"last_address": "0x20000000"},
                                    CLEANERS["memory_viewer"]),
        )

    def all(self) -> List[JsonStore]:
        return [self.favorites, self.actions, self.watch_list, self.data_logger, self.custom_functions,
                self.sequences, self.formulas, self.notes, self.preferences, self.hardware_config,
                self.signal_generator, self.ble_packet, self.memory_viewer]

    def problems(self) -> List[Problem]:
        """What the last load of every file skipped."""
        return [p for store in self.all() for p in store.problems]
