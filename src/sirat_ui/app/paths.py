"""Resource and data locations. Works from source and from a PyInstaller bundle."""

from __future__ import annotations

import sys
from pathlib import Path


def package_dir() -> Path:
    # PyInstaller unpacks data next to the frozen package under sys._MEIPASS
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "sirat_ui" if base else Path(__file__).resolve().parent.parent


def qml_dir() -> Path:
    return package_dir() / "qml"


def samples_dir() -> Path:
    """Sample files for trying features out: docs/samples from source, samples/ in a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "samples" if base else package_dir().parent.parent / "docs" / "samples"


def default_home(backend: str) -> Path:
    """The fake backend keeps its data in a demo folder so it never touches real SiRAT settings."""
    home = Path.home()
    return home / ".sirat" / "demo_home" if backend == "fake" else home


def session_log_dir() -> Path:
    """Req 1: per-session debug log."""
    return Path("C:/temp/sirat") if sys.platform == "win32" else Path.home() / ".sirat" / "session_logs"


def dumps_dir() -> Path:
    """Req 12: dump CSVs, next to the session logs. Never cleaned up automatically."""
    return session_log_dir() / "dumps"


def daily_log_dir() -> Path:
    """Req 35: daily log files, kept 30 days. Always under the real home, even for the fake backend."""
    return Path.home() / ".sirat" / "logs"
