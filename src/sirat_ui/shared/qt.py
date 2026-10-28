"""Qt names that PyQt5's bundled type stubs leave out or mistype, re-exported with real types so pyrefly can
check the code that uses them.

Import these from here instead of PyQt5.QtCore.
"""

from __future__ import annotations

from typing import Any

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QtMsgType

# Shim: PyQt5 5.15 ships QtCore.pyi without pyqtProperty, so `from PyQt5.QtCore import pyqtProperty` is a type
# error (missing-module-attribute) even though it works at runtime. Fetching it with getattr gives every
# ViewModel one import that type-checks. It's typed Any because pyqtProperty is both a decorator and a
# descriptor factory (pyqtProperty(type, fget, notify=...)), which a precise signature can't express without
# full Qt stubs. The real type safety is on the Python side: the getters and slots it wraps are annotated.
# Remove this module if the project moves to PyQt6 or adds stubs that declare pyqtProperty.
pyqtProperty: Any = getattr(QtCore, "pyqtProperty")  # noqa: N816 (Qt's name)

# Shim: the same stubs declare enum values as `Name = ...  # type: Qt.SomeEnum`. pyrefly doesn't read type
# comments, so it sees them as Ellipsis. These are the few values the app uses, with their real types.
USER_ROLE: int = int(getattr(Qt, "UserRole"))
DISPLAY_ROLE: int = int(getattr(Qt, "DisplayRole"))
AA_ENABLE_HIGH_DPI_SCALING: "Qt.ApplicationAttribute" = getattr(Qt, "AA_EnableHighDpiScaling")
AA_USE_HIGH_DPI_PIXMAPS: "Qt.ApplicationAttribute" = getattr(Qt, "AA_UseHighDpiPixmaps")
QT_WARNING_MSG: int = int(getattr(QtMsgType, "QtWarningMsg"))
QT_CRITICAL_MSG: int = int(getattr(QtMsgType, "QtCriticalMsg"))
QT_FATAL_MSG: int = int(getattr(QtMsgType, "QtFatalMsg"))
