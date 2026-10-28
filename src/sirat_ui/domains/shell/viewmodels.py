"""Shell ViewModels: global state for the top bar/status bar, and the root VM QML sees as `app`."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.shell.pages import PAGES, page_source
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, qprop
from sirat_ui.state.preferences import PreferencesState
from sirat_ui.state.station import StationState
from sirat_ui.state.status import StatusLine



class StateViewModel(BaseViewModel):
    """Read-only mirror of StationState for QML."""

    changed = pyqtSignal()

    def __init__(self, state: StationState, prefs: PreferencesState, status: StatusLine, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._prefs = prefs
        self._status = status
        self._refresh()
        state.changed.connect(self._refresh)
        prefs.changed.connect(lambda _: self._refresh())
        status.changed.connect(self._refresh)

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
            backend_text=s.backend_label, status_message=self._status.text, dark_mode=self._prefs.value.dark_mode,
        )

    @pyqtSlot(int)
    def setPosition(self, position: int) -> None:  # noqa: N802
        self._state.set_position(position)

    @pyqtSlot()
    def toggleDarkMode(self) -> None:  # noqa: N802
        self._prefs.update(dark_mode=not self._prefs.value.dark_mode)


class ShellViewModel(BaseViewModel):
    """The root VM, exposed to QML as the `app` context property.

    Build it with with_children(): each child ViewModel becomes a constant property of the same name
    (app.detail, app.dumps ...), so registering a ViewModel in the container is all QML needs.
    """

    changed = pyqtSignal()

    def __init__(self, children: Dict[str, QObject], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._children = children
        for child in children.values():
            child.setParent(self)
        self._current_page = "registers"
        self._dock_follow(self._current_page)

    currentPage = qprop(str, "_current_page", changed)

    @pyqtProperty("QVariantList", constant=True)
    def pages(self) -> List[Dict[str, Any]]:
        return PAGES

    @pyqtSlot(str, result="QString")
    def pageSource(self, key: str) -> str:  # noqa: N802
        """The page's QML file, relative to qml/shell/ (domains/shell/pages.py)."""
        return page_source(key)

    @pyqtSlot(str)
    def navigate(self, key: str) -> None:
        if any(p["key"] == key for p in PAGES):
            self._update(current_page=key)
            self._dock_follow(key)

    def _dock_follow(self, key: str) -> None:
        """The dock remembers open/collapsed per page."""
        dock = self._children.get("dock")
        if dock is not None:
            getattr(dock, "setPage")(key)

    def child(self, name: str) -> QObject:
        return self._children[name]


def _child_property(name: str) -> pyqtProperty:
    def get(self: ShellViewModel) -> QObject:
        return self.child(name)
    return pyqtProperty(QObject, get, constant=True)


def with_children(children: Dict[str, QObject]) -> ShellViewModel:
    """A ShellViewModel whose class has one constant QObject property per child (Qt needs them on the class)."""
    cls = type("ShellViewModel", (ShellViewModel,), {name: _child_property(name) for name in children})
    return cls(children)
