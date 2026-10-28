"""Page objects: tests talk in user terms ("open register", "click Write"); clicking details live here.

Elements are found by objectName, never by position, so layout changes in Design Studio don't break tests.
"""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QObject, QPointF, Qt
from PyQt5.QtGui import QGuiApplication, QKeyEvent
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtTest import QTest


class Ui:
    def __init__(self, app, qtbot) -> None:
        self.app = app
        self.window = app.window
        self.qtbot = qtbot

    # ---- primitives ---------------------------------------------------------------------------

    def lookup(self, name: str):
        """QObject children (popups) and the visual tree (list delegates have no QObject parent).

        The same panel can exist twice (e.g. the log in the dock and in its pop-out window), so a
        visible match wins over a hidden one.
        """
        matches = list(self.window.findChildren(QObject, name))
        stack = [self.window.contentItem()]
        while stack:
            item = stack.pop()
            if item.objectName() == name and item not in matches:
                matches.append(item)
            # Popups (tooltips, menus) aren't items; when a Repeater made their owner, they're only reachable
            # as that item's direct QObject children.
            for child in item.findChildren(QObject, name, Qt.FindDirectChildrenOnly):
                if child not in matches:
                    matches.append(child)
            stack.extend(item.childItems())
        # Items in a hidden window still report visible=true, so also require the item's own window.
        def on_screen(obj) -> bool:
            in_main = not isinstance(obj, QQuickItem) or obj.window() is self.window
            return in_main and bool(obj.property("visible"))

        visible = [m for m in matches if on_screen(m)]
        return (visible or matches or [None])[0]

    def find(self, name: str) -> QQuickItem:
        item = self.lookup(name)
        assert item is not None, f"no element named {name!r}"
        return item

    def exists(self, name: str) -> bool:
        return self.lookup(name) is not None

    def visible(self, name: str) -> bool:
        item = self.lookup(name)
        return bool(item and item.property("visible"))

    def settle(self, ms: int = 30) -> None:
        self.qtbot.wait(ms)

    def click(self, name: str, double: bool = False) -> None:
        item = self.find(name)
        assert item.property("visible") and item.property("enabled"), f"{name} isn't clickable"
        center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        if double:
            QTest.mouseDClick(self.window, Qt.LeftButton, Qt.NoModifier, center)
        else:
            QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, center)
        self.settle()

    def type_text(self, name: str, text: str, enter: bool = True) -> None:
        field = self.find(name)
        field.forceActiveFocus()
        field.setProperty("text", "")
        for char in text:
            self._key(0, char)
        if enter:
            self._key(Qt.Key_Return, "\r")
        self.settle()

    def _key(self, key: int, text: str) -> None:
        for kind in (QEvent.KeyPress, QEvent.KeyRelease):
            QGuiApplication.sendEvent(self.window, QKeyEvent(kind, key, Qt.NoModifier, text))

    def text(self, name: str) -> str:
        return str(self.find(name).property("text"))

    def enabled(self, name: str) -> bool:
        return bool(self.find(name).property("enabled"))

    def wait_for(self, predicate, timeout: int = 2000) -> None:
        self.qtbot.waitUntil(predicate, timeout=timeout)

    def navigate(self, page: str) -> None:
        self.click(f"nav_{page}")


class RegistersPage(Ui):
    def search(self, text: str) -> None:
        self.type_text("treeSearchField", text)

    def open_register(self, full_name: str) -> None:
        peripheral = full_name.split(".")[0]
        self.wait_for(lambda: self.exists(f"treeRow_{peripheral}"))
        if not self.exists(f"treeRow_{full_name}"):
            self.click(f"treeRow_{peripheral}")
            self.wait_for(lambda: self.exists(f"treeRow_{full_name}"))
        self.click(f"treeRow_{full_name}")
        self.wait_for(lambda: self.text("detailTitle") == full_name)

    def value_text(self) -> str:
        return self.text("registerValueField")

    def write(self, value: str) -> None:
        self.type_text("registerValueField", value, enter=False)
        self.click("writeButton")

    def toggle_bit(self, bit: int) -> None:
        self.click(f"bit_{bit}")


class Dialogs(Ui):
    def confirm_open(self) -> bool:
        return self.visible("confirmDialog")

    def cancel_confirm(self) -> None:
        self.click("confirmCancelButton")

    def accept_confirm(self) -> None:
        self.click("confirmAcceptButton")

    def alert_open(self) -> bool:
        return self.visible("alertDialog")

    def recovery_open(self) -> bool:
        return self.visible("disconnectDialog")
