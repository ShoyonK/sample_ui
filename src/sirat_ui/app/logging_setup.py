"""Logging to the console and to both log files the requirements ask for.

- Session log (req 1):  C:/temp/sirat/session_log_<YYYYMMDD_HHMMSS>.log
                        "<timestamp> - <level> - <logger_name> - <message>"
- Daily log (req 35):   ~/.sirat/logs/sirat_<YYYY-MM-DD>.log, a new file each day, kept 30 days
                        "[YYYY-MM-DD HH:MM:SS.mmm] [LEVEL] Message"
"""

from __future__ import annotations

import datetime as dt
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Optional

RETENTION_DAYS = 30
SESSION_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


class DailyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        stamp = dt.datetime.fromtimestamp(record.created)
        return f"[{stamp:%Y-%m-%d %H:%M:%S}.{int(record.msecs):03d}] [{record.levelname}] {record.getMessage()}"


class DailyFileHandler(logging.Handler):
    """Writes to sirat_<date>.log, switching files when the date changes; prunes old files on start."""

    def __init__(self, directory: Path, retention_days: int = RETENTION_DAYS,
                 today: Callable[[], dt.date] = dt.date.today) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.retention_days = retention_days
        self._today = today
        self._date: Optional[dt.date] = None
        self._stream = None
        self.setFormatter(DailyFormatter())
        self.directory.mkdir(parents=True, exist_ok=True)
        self.prune()

    def path_for(self, day: dt.date) -> Path:
        return self.directory / f"sirat_{day:%Y-%m-%d}.log"

    def prune(self) -> None:
        cutoff = self._today() - dt.timedelta(days=self.retention_days)
        for path in self.directory.glob("sirat_*.log"):
            try:
                day = dt.datetime.strptime(path.stem[len("sirat_"):], "%Y-%m-%d").date()
            except ValueError:
                continue
            if day < cutoff:
                path.unlink(missing_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            day = self._today()
            if day != self._date or self._stream is None:
                self._open(day)
            stream = self._stream
            if stream is not None:
                stream.write(self.format(record) + "\n")
                stream.flush()
        except Exception:  # logging must never take the app down
            self.handleError(record)

    def _open(self, day: dt.date) -> None:
        if self._stream:
            self._stream.close()
        self._date = day
        self._stream = self.path_for(day).open("a", encoding="utf-8")

    def close(self) -> None:
        if self._stream:
            self._stream.close()
            self._stream = None
        super().close()


def setup_logging(level: int, session_dir: Path, daily_dir: Path) -> Optional[Path]:
    """Installs console, session and daily handlers once. Returns the session log path."""
    root = logging.getLogger()
    if any(isinstance(h, DailyFileHandler) for h in root.handlers):
        return None
    root.setLevel(level)
    if sys.stderr is not None:  # a windowed .exe has no console
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(SESSION_FORMAT))
        root.addHandler(console)
    session_path = None
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        session_path = session_dir / f"session_log_{time.strftime('%Y%m%d_%H%M%S')}.log"
        session = logging.FileHandler(session_path, encoding="utf-8")
        session.setFormatter(logging.Formatter(SESSION_FORMAT))
        root.addHandler(session)
    except OSError:
        session_path = None
    try:
        root.addHandler(DailyFileHandler(daily_dir))
    except OSError:
        pass
    return session_path
