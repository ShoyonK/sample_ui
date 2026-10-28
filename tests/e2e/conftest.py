from __future__ import annotations

import pytest
from PyQt5.QtCore import QtMsgType

from support import Harness
from sirat_ui.app.application import Application


class RunningApp:
    def __init__(self, harness: Harness, app: Application) -> None:
        self.h = harness
        self.app = app
        self.window = app.window


def _launch(qapp, qtbot, harness: Harness) -> RunningApp:
    app = Application(qapp, harness.container, owns_qt_app=False)
    app.load()
    app.window.resize(1600, 950)
    qtbot.waitExposed(app.window)
    qtbot.wait(50)
    return RunningApp(harness, app)


@pytest.fixture
def running(qapp, qtbot, tmp_path):
    running = _launch(qapp, qtbot, Harness(tmp_path, real_dialogs=True))
    yield running
    running.app.shutdown()


@pytest.fixture
def running_disconnected(qapp, qtbot, tmp_path):
    running = _launch(qapp, qtbot, Harness(tmp_path, connect=False, real_dialogs=True))
    yield running
    running.app.shutdown()


@pytest.fixture(autouse=True)
def no_qml_warnings(qtlog):
    """Any QML warning (broken binding, missing property, type error) fails the test."""
    yield
    problems = [r.message for r in qtlog.records
                if r.type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg)
                and "QFontDatabase" not in r.message and "Note that Qt no longer ships fonts" not in r.message
                and "This plugin does not support raise()" not in r.message]  # offscreen platform can't raise windows
    assert problems == []
