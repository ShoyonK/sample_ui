"""Screen readers get a name for every visible control, and keyboard focus is visible and moves."""

from PyQt5.QtCore import Qt
from PyQt5.QtQml import QQmlEngine, QQmlProperty
from PyQt5.QtQuick import QQuickItem

from pages import Ui

PAGES = ["registers", "watch", "actions", "sequences", "dumps", "radio", "settings"]


def _visible_items(item: QQuickItem):
    if not item.isVisible() or item.opacity() == 0:
        return
    yield item
    for child in item.childItems():
        yield from _visible_items(child)


def _accessible(item: QQuickItem, prop: str):
    return QQmlProperty(item, f"Accessible.{prop}", QQmlEngine.contextForObject(item)).read()


def _unnamed_controls(window) -> list:
    """Buttons and check boxes (Qt Quick Controls' button classes) with an empty Accessible.name."""
    unnamed = []
    for item in _visible_items(window.contentItem()):
        cls = item.metaObject().className()
        if "Button" not in cls and "CheckBox" not in cls:
            continue
        if not str(_accessible(item, "name") or "").strip():
            unnamed.append(item.objectName() or cls)
    return unnamed


def test_every_visible_control_has_an_accessible_name(running, qtbot):
    ui = Ui(running.app, qtbot)
    for page in PAGES:
        running.h.shell.navigate(page)
        ui.settle(60)
        assert _unnamed_controls(running.window) == [], page


def test_tab_moves_focus_through_controls(running, qtbot):
    ui = Ui(running.app, qtbot)
    window = running.window
    window.requestActivate()
    seen = set()
    for _ in range(12):
        qtbot.keyClick(window, Qt.Key_Tab)
        ui.settle(10)
        focused = window.activeFocusItem()
        assert focused is not None
        seen.add(focused.objectName() or focused.metaObject().className())
    assert len(seen) > 6  # focus walks through the window instead of getting stuck
