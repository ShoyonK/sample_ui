"""Pydantic validation for everything SiRAT reads from disk: the settings files, sessions and settings exports.

This is the boundary where outside data comes in. Inside the app, typed dataclasses are used and pyrefly checks
them; pydantic only runs here, on load.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from sirat_ui.models.settings import Problem
from sirat_ui.stores.schemas.files import (clean_ble_packet, clean_custom_functions, clean_data_logger,
                                           clean_favorites, clean_formulas, clean_hardware_config, clean_memory_viewer,
                                           clean_notes,
                                           clean_preferences, clean_sequences, clean_signal_generator,
                                           clean_watch_list)
from sirat_ui.stores.schemas.operations import clean_actions, validate_operation
from sirat_ui.stores.schemas.report import Report
from sirat_ui.stores.schemas.session import SettingsBundle, clean_session

Cleaner = Callable[[Any, Report], Any]

# Settings export "files" keys -> the cleaner for that file (domains/settings/transfer.py uses the same names).
CLEANERS: Dict[str, Cleaner] = {
    "favorites": clean_favorites, "actions": clean_actions, "watch_list": clean_watch_list,
    "data_logger": clean_data_logger, "custom_functions": clean_custom_functions, "sequences": clean_sequences,
    "field_formulas": clean_formulas, "field_notes": clean_notes, "preferences": clean_preferences,
    "hardware_config": clean_hardware_config, "signal_generator": clean_signal_generator,
    "ble_packet": clean_ble_packet,
    "memory_viewer": clean_memory_viewer,
}

__all__ = ["CLEANERS", "Cleaner", "Problem", "Report", "SettingsBundle", "clean_actions", "clean_session",
           "validate_operation"]
