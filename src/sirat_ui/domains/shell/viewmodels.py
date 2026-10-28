"""Shell ViewModels: global state for the top bar/status bar, and the root VM QML sees as `app`."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.shared.viewmodel import BaseViewModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

PAGES: List[Dict[str, Any]] = [
    {"key": "registers", "title": "Registers", "icon": "cpu", "ready": True},
    {"key": "watch", "title": "Watch and logger", "icon": "pulse", "ready": True},
    {"key": "actions", "title": "Actions", "icon": "bolt", "ready": True},
    {"key": "sequences", "title": "Sequences", "icon": "list", "ready": True},
    {"key": "dumps", "title": "Dumps and diffs", "icon": "compare", "ready": True},
    {"key": "radio", "title": "Radio and PHY", "icon": "antenna", "ready": True},
    {"key": "instruments", "title": "Instruments", "icon": "wave", "ready": False},
    {"key": "advanced", "title": "Advanced", "icon": "terminal", "ready": False},
    {"key": "tests", "title": "Tests", "icon": "flask", "ready": False},
    {"key": "settings", "title": "Settings", "icon": "settings", "ready": True},
]


class StateViewModel(BaseViewModel):
    """Read-only mirror of AppState for QML."""

    changed = pyqtSignal()

    def __init__(self, state: AppState, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._refresh()
        state.changed.connect(self._refresh)
        state.preferences_changed.connect(lambda _: self._refresh())

    position = qprop(int, "_position", changed)
    connected = qprop(bool, "_connected", changed)
    connectionText = qprop(str, "_connection_text", changed)
    connectionLevel = qprop(str, "_connection_level", changed)
    chipLabel = qprop(str, "_chip_label", changed)
    chipShort = qprop(str, "_chip_short", changed)
    phyText = qprop(str, "_phy_text", changed)
    activityText = qprop(str, "_activity_text", changed)
    releaseText = qprop(str, "_release_text", changed)
    backendText = qprop(str, "_backend_text", changed)
    statusMessage = qprop(str, "_status_message", changed)
    darkMode = qprop(bool, "_dark_mode", changed)

    def _refresh(self) -> None:
        s, facts = self._state, self._state.facts
        if s.connecting:
            text, level = "Connecting…", "busy"
        elif facts.fault:
            text, level = "Fault", "danger"
        elif facts.dut_connected:
            text, level = "Connected", "ok"
        else:
            text, level = "Disconnected", "danger"
        self._update(
            position=s.position, connected=facts.dut_connected, connection_text=text, connection_level=level,
            chip_label=s.chip.label if s.chip else "No chip", chip_short=s.chip.short if s.chip else "",
            phy_text=f"PHY · {facts.phy}" if facts.phy else "", activity_text=f"Activity {facts.activity}",
            release_text=f"Service {s.release_id}" if s.release_id else "Service offline",
            backend_text=s.backend_label, status_message=s.status_message, dark_mode=s.preferences.dark_mode,
        )

    @pyqtSlot(int)
    def setPosition(self, position: int) -> None:  # noqa: N802
        self._state.set_position(position)

    @pyqtSlot()
    def toggleDarkMode(self) -> None:  # noqa: N802
        self._state.update_preferences(dark_mode=not self._state.preferences.dark_mode)


class ShellViewModel(BaseViewModel):
    """The root VM, exposed to QML as the `app` context property. Child VMs are constant properties."""

    changed = pyqtSignal()

    def __init__(self, children: Dict[str, QObject], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._children = children
        for child in children.values():
            child.setParent(self)
        self._current_page = "registers"

    currentPage = qprop(str, "_current_page", changed)

    @pyqtProperty("QVariantList", constant=True)
    def pages(self) -> List[Dict[str, Any]]:
        return PAGES

    @pyqtSlot(str)
    def navigate(self, key: str) -> None:
        if any(p["key"] == key for p in PAGES):
            self._update(current_page=key)

    def child(self, name: str) -> QObject:
        return self._children[name]

    state = pyqtProperty(QObject, lambda self: self._children["state"], constant=True)
    settings = pyqtProperty(QObject, lambda self: self._children["settings"], constant=True)
    dialogs = pyqtProperty(QObject, lambda self: self._children["dialogs"], constant=True)
    connection = pyqtProperty(QObject, lambda self: self._children["connection"], constant=True)
    recovery = pyqtProperty(QObject, lambda self: self._children["recovery"], constant=True)
    tree = pyqtProperty(QObject, lambda self: self._children["tree"], constant=True)
    favorites = pyqtProperty(QObject, lambda self: self._children["favorites"], constant=True)
    detail = pyqtProperty(QObject, lambda self: self._children["detail"], constant=True)
    history = pyqtProperty(QObject, lambda self: self._children["history"], constant=True)
    actions = pyqtProperty(QObject, lambda self: self._children["actions"], constant=True)
    actionEditor = pyqtProperty(QObject, lambda self: self._children["actionEditor"], constant=True)
    formulaEditor = pyqtProperty(QObject, lambda self: self._children["formulaEditor"], constant=True)
    readAll = pyqtProperty(QObject, lambda self: self._children["readAll"], constant=True)
    palette = pyqtProperty(QObject, lambda self: self._children["palette"], constant=True)
    hardware = pyqtProperty(QObject, lambda self: self._children["hardware"], constant=True)
    systemInfo = pyqtProperty(QObject, lambda self: self._children["systemInfo"], constant=True)
    sessions = pyqtProperty(QObject, lambda self: self._children["sessions"], constant=True)
    dumps = pyqtProperty(QObject, lambda self: self._children["dumps"], constant=True)
    lpwPhy = pyqtProperty(QObject, lambda self: self._children["lpwPhy"], constant=True)
    wifiPhy = pyqtProperty(QObject, lambda self: self._children["wifiPhy"], constant=True)
    prs = pyqtProperty(QObject, lambda self: self._children["prs"], constant=True)
    windows = pyqtProperty(QObject, lambda self: self._children["windows"], constant=True)
    log = pyqtProperty(QObject, lambda self: self._children["log"], constant=True)
    watch = pyqtProperty(QObject, lambda self: self._children["watch"], constant=True)
    logger = pyqtProperty(QObject, lambda self: self._children["logger"], constant=True)
    sequences = pyqtProperty(QObject, lambda self: self._children["sequences"], constant=True)
