"""The one-time import of what the old tool (SiRAT) saved, into ~/.sibench.

SiRAT kept six settings files next to the home folder (~/.sirat_favorites.json and so on) and the rest in
~/.sirat/. The formats are the same (stores/formats.py), so the files are copied as they are; the stores clean
them up on load like any other file. The old files stay where they are, so the old tool keeps working.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger("SiBench.stores")

# (where SiRAT kept it, relative to home; its name in ~/.sibench)
LEGACY_FILES: Tuple[Tuple[str, str], ...] = (
    (".sirat_favorites.json", "favorites.json"),
    (".sirat_actions.json", "actions.json"),
    (".sirat_watch_list.json", "watch_list.json"),
    (".sirat_data_logger.json", "data_logger.json"),
    (".sirat_custom_functions.json", "custom_functions.json"),
    (".sirat_sequences.json", "sequences.json"),
    (".sirat/field_formulas.json", "field_formulas.json"),
    (".sirat/field_notes.json", "field_notes.json"),
    (".sirat/preferences.json", "preferences.json"),
    (".sirat/hardware_config.json", "hardware_config.json"),
    (".sirat/signal_generator.json", "signal_generator.json"),
    (".sirat/ble_packet.json", "ble_packet.json"),
    (".sirat/memory_viewer.json", "memory_viewer.json"),
    (".sirat/autosave.json", "autosave.json"),
)
LEGACY_FOLDERS: Tuple[Tuple[str, str], ...] = ((".sirat/sessions", "sessions"),)


def import_legacy_data(home: Path) -> List[str]:
    """Copies SiRAT's saved files into home/.sibench, only on the first launch (no ~/.sibench yet).

    Returns what it copied, by its new name. A file that can't be copied is logged and skipped: the app then
    starts with that file's defaults, and the old file is still there to copy by hand.
    """
    home = Path(home)
    target = home / ".sibench"
    if target.exists():
        return []
    copied: List[str] = []
    for old, new in LEGACY_FILES + LEGACY_FOLDERS:
        source = home / old
        if not source.exists():
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target / new)
            else:
                shutil.copy2(source, target / new)
        except OSError as exc:
            log.warning("Couldn't import %s from SiRAT: %s", source, exc)
            continue
        copied.append(new)
    if copied:
        log.info("Imported from SiRAT into %s: %s", target, ", ".join(copied))
    return copied
