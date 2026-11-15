"""The app's pages: the one table to edit when a page is added.

The nav rail, the page host, pop-out windows and Ctrl+K page entries all read it. `source` is relative to
qml/shell/, where the page loaders live. A page's parts that open in their own window are in tools.py.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sirat_ui.domains.shell.tools import page_parts

_PAGES: List[Dict[str, Any]] = [
    {"key": "registers", "title": "Registers", "label": "Registers", "icon": "cpu", "ready": True,
     "source": "../pages/registers/RegistersPage.qml"},
    {"key": "watch", "title": "Watch and logger", "label": "Watch", "icon": "pulse", "ready": True,
     "source": "../pages/watch/WatchPage.qml"},
    {"key": "actions", "title": "Actions", "label": "Actions", "icon": "bolt", "ready": True,
     "source": "../pages/actions/ActionsPage.qml"},
    {"key": "sequences", "title": "Sequences", "label": "Sequences", "icon": "list", "ready": True,
     "source": "../pages/sequences/SequencesPage.qml"},
    {"key": "dumps", "title": "Diffs", "label": "Diffs", "icon": "compare", "ready": True,
     "source": "../pages/dumps/DumpsPage.qml"},
    {"key": "radio", "title": "Radio and PHY", "label": "Radio", "icon": "antenna", "ready": True,
     "source": "../pages/radio/RadioPage.qml"},
    {"key": "instruments", "title": "Instruments", "label": "Instruments", "icon": "wave", "ready": True,
     "source": "../pages/instruments/InstrumentsPage.qml"},
    {"key": "advanced", "title": "Advanced", "label": "Advanced", "icon": "terminal", "ready": True,
     "source": "../pages/advanced/AdvancedPage.qml"},
    {"key": "tests", "title": "Test execution", "label": "Tests", "icon": "flask", "ready": True,
     "source": "../pages/tests/TestsPage.qml"},
    {"key": "settings", "title": "Settings", "label": "Settings", "icon": "settings", "ready": True,
     "source": "../pages/settings/SettingsPage.qml"},
]

# "parts": the nav rail's right-click menu lists them
PAGES: List[Dict[str, Any]] = [{**page, "parts": page_parts(page["key"])} for page in _PAGES]


def page_source(key: str) -> str:
    """The page's QML file, relative to qml/shell/, or "" for an unknown key."""
    return next((p["source"] for p in PAGES if p["key"] == key), "")
