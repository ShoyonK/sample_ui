"""Application: creates (or reuses) the Qt application, builds the container and loads Main.qml."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import qInstallMessageHandler, QMessageLogContext, QObject, Qt, QtMsgType, QUrl
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtQuick import QQuickWindow  # registers the type so rootObjects() returns a QQuickWindow
from PyQt5 import sip
from PyQt5.QtWidgets import QApplication

from sirat_ui import __version__
from sirat_ui.app.container import ServiceContainer
from sirat_ui.app.paths import qml_dir
from sirat_ui.shared.qt import (AA_ENABLE_HIGH_DPI_SCALING, AA_USE_HIGH_DPI_PIXMAPS, QT_CRITICAL_MSG, QT_FATAL_MSG,
                               QT_WARNING_MSG)

log = logging.getLogger("SiRAT.app")


_QT_LEVELS: Dict[int, int] = {QT_WARNING_MSG: logging.WARNING, QT_CRITICAL_MSG: logging.ERROR,
                              QT_FATAL_MSG: logging.CRITICAL}


def _qt_message_handler(mode: QtMsgType, context: QMessageLogContext, message: Optional[str]) -> None:
    logging.getLogger("SiRAT.qml").log(_QT_LEVELS.get(int(mode), logging.DEBUG), message or "")


def ensure_qt_app(argv: Optional[List[str]] = None) -> Tuple[QApplication, bool]:
    """Creates the QApplication, or reuses one (e.g. inside PyCharm). Returns (app, created)."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing, False
    QGuiApplication.setAttribute(AA_ENABLE_HIGH_DPI_SCALING, True)
    QGuiApplication.setAttribute(AA_USE_HIGH_DPI_PIXMAPS, True)
    app = QApplication(argv or ["sirat"])
    app.setApplicationName("SiRAT")
    app.setApplicationVersion(__version__)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Default")
    qInstallMessageHandler(_qt_message_handler)
    return app, True


class Application:
    """Build the QApplication with ensure_qt_app() before the container, since VMs own QTimers."""

    def __init__(self, qt_app: QApplication, container: ServiceContainer, owns_qt_app: bool = True) -> None:
        self.qt_app = qt_app  # keep a Python reference, or PyQt destroys the QApplication
        self.owns_qt_app = owns_qt_app
        self.container = container
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(qml_dir()))
        context = engine.rootContext()
        assert context is not None  # an engine always has a root context
        context.setContextProperty("app", container.shell)
        self.engine: Optional[QQmlApplicationEngine] = engine
        self.window: Optional[QQuickWindow] = None
        qt_app.aboutToQuit.connect(self.shutdown)

    def load(self) -> QQuickWindow:
        main = qml_dir() / "Main.qml"
        if self.engine is None:
            raise RuntimeError("The application was shut down")
        self.engine.load(QUrl.fromLocalFile(str(main)))
        roots = self.engine.rootObjects()
        window = roots[0] if roots else None
        if not isinstance(window, QQuickWindow):
            raise RuntimeError(f"Couldn't load {main}; see the session log for QML errors")
        self.window = window
        icon = qml_dir() / "assets" / "sirat.png"
        if icon.exists():
            self.qt_app.setWindowIcon(QIcon(str(icon)))
        return self.window

    def bring_to_front(self) -> None:
        if self.window is not None:
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()

    def exec(self) -> int:
        return self.qt_app.exec_()

    def shutdown(self) -> None:
        """Destroys QML before the ViewModels it binds to, so teardown doesn't spam binding errors."""
        if self.engine is None:
            return
        self.container.stop()
        engine, self.engine, self.window = self.engine, None, None
        sip.delete(engine)  # synchronous: the engine destroys its root objects first

    def root(self) -> Optional[QQuickWindow]:
        return self.window
