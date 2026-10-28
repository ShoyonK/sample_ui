"""Entry points: `sirat` / `python -m sirat_ui` (standalone) and launch_viewer() (req §1, from a test context)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from sirat_ui.app.application import Application, ensure_qt_app
from sirat_ui.app.container import ServiceContainer
from sirat_ui.app.logging_setup import setup_logging
from sirat_ui.app.paths import daily_log_dir, default_home, dumps_dir, session_log_dir
from sirat_ui.app.qt_scheduler import QtScheduler
from sirat_ui.gateway.fake.fake_station import FakeStationGateway
from sirat_ui.gateway.fake.scenarios import SCENARIOS, apply_scenario
from sirat_ui.stores.demo_data import seed_demo_data
from sirat_ui.stores.json_store import UserStores

_running: Optional[Application] = None


def build_app(backend: str = "fake", scenario: str = "happy", home: Optional[Path] = None,
              seed_demo: bool = True, argv: Optional[List[str]] = None, dumps: Optional[Path] = None):
    if backend != "fake":
        raise SystemExit("The real Station API client isn't available yet. Run with --backend fake.")
    home = home or default_home(backend)
    if seed_demo:
        seed_demo_data(UserStores.in_home(home))
    qt_app, created = ensure_qt_app(argv)
    scheduler = QtScheduler()
    gateway = FakeStationGateway(scheduler)
    chosen = apply_scenario(gateway, scenario)
    container = ServiceContainer(gateway, home, scheduler, backend_label=f"Fake backend · scenario {scenario}",
                                 dumps_dir=dumps or dumps_dir())
    return Application(qt_app, container, owns_qt_app=created), chosen


def _parse(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sirat", description="SiRAT register access tool")
    parser.add_argument("--backend", choices=["fake", "api"], default="fake")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="happy",
                        help="fake backend scenario")
    parser.add_argument("--home", type=Path, default=None, help="folder holding user settings")
    parser.add_argument("--no-demo-data", action="store_true", help="don't seed demo favorites/actions")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse(sys.argv[1:] if argv is None else argv)
    log_path = setup_logging(getattr(logging, str(args.log_level).upper(), logging.INFO),
                             session_log_dir(), daily_log_dir())
    app, scenario = build_app(args.backend, args.scenario, args.home, not args.no_demo_data)
    if log_path:
        logging.getLogger("SiRAT").info("Session log: %s", log_path)
    window = app.load()
    window.showMaximized()  # req 1: initial state maximized
    app.container.start(autoconnect=scenario.autoconnect, position=app.container.state.position)
    return app.exec()


def launch_viewer(parent: object = None, log_level: int = logging.INFO, scenario: str = "happy") -> int:
    """Blocking launch from Python/PyCharm. A second call brings the existing window to front."""
    global _running
    if _running is not None:
        _running.bring_to_front()
        return 0
    setup_logging(log_level, session_log_dir(), daily_log_dir())
    app, chosen = build_app("fake", scenario)
    _running = app
    app.load()
    app.container.start(autoconnect=chosen.autoconnect)
    try:
        return app.exec() if app.owns_qt_app else 0
    finally:
        if app.owns_qt_app:
            _running = None


def launch_viewer_async(parent: object = None, log_level: int = logging.INFO, scenario: str = "happy") -> Application:
    """Non-blocking: needs a Qt event loop already running in this thread (e.g. PyCharm's Qt integration)."""
    global _running
    if _running is not None:
        _running.bring_to_front()
        return _running
    setup_logging(log_level, session_log_dir(), daily_log_dir())
    app, chosen = build_app("fake", scenario)
    _running = app
    app.load()
    app.container.start(autoconnect=chosen.autoconnect)
    return app
