"""Entry points: `sirat` / `python -m sirat_ui` (standalone) and launch_viewer() (req §1, from a test context)."""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from sirat_ui.app import crash_guard
from sirat_ui.app.application import Application, ensure_qt_app
from sirat_ui.app.container import ServiceContainer
from sirat_ui.app.logging_setup import setup_logging
from sirat_ui.app.paths import daily_log_dir, default_home, dumps_dir, session_log_dir
from sirat_ui.app.qt_post import QtPoster
from sirat_ui.app.qt_scheduler import QtScheduler
from sirat_ui.gateway.api.client import ApiStationGateway
from sirat_ui.gateway.fake.chip import build_chip
from sirat_ui.gateway.fake.fake_station import FakeStationGateway
from sirat_ui.gateway.fake.scenarios import SCENARIOS, Scenario, apply_scenario
from sirat_ui.gateway.fake.server import DEFAULT_PORT, serve
from sirat_ui.gateway.port import StationGateway
from sirat_ui.stores.demo_data import seed_demo_data, seed_demo_dumps
from sirat_ui.stores.json_store import UserStores

_running: Optional[Application] = None


BACKENDS = ("fake", "fake-tcp", "api")


def build_app(backend: str = "fake", scenario: str = "happy", home: Optional[Path] = None,
              seed_demo: bool = True, argv: Optional[List[str]] = None, dumps: Optional[Path] = None,
              host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> Tuple[Application, Scenario]:
    """Builds the application on one of three backends (docs/JSONRPC_MIGRATION.md section 5):

    - fake: the fake station in this process, with a scenario applied;
    - fake-tcp: the fake station behind a TCP server in this process, reached over JSON-RPC like a real one;
    - api: the station service at host:port.

    Demo data is only seeded for the fake backends, so a real station's home folder is never touched. The fake
    backends keep their dumps in the demo home too (with three demo dumps to compare), not in the real dumps folder.
    """
    if backend not in BACKENDS:
        raise SystemExit(f"Unknown backend {backend!r}. Choose one of: {', '.join(BACKENDS)}")
    home = home or default_home(backend)
    if dumps is None:
        dumps = dumps_dir() if backend == "api" else home / ".sirat" / "dumps"
    if seed_demo and backend != "api":
        seed_demo_data(UserStores.in_home(home))
        seed_demo_dumps(dumps, build_chip(), dt.date.today())
    qt_app, created = ensure_qt_app(argv)
    scheduler = QtScheduler()
    gateway: StationGateway
    if backend == "fake":
        fake = FakeStationGateway(scheduler)
        chosen = apply_scenario(fake, scenario)
        gateway, label = fake, f"Fake backend · scenario {scenario}"
    else:
        if backend == "fake-tcp":
            server, chosen = serve(port=0, scenario=scenario)
            host, port = server.address
            label = f"Fake backend over TCP ({host}:{port}) · scenario {scenario}"
        else:   # a real station: nothing connects to a DUT until the user asks
            chosen = Scenario("station", "A station service", autoconnect=False)
            label = f"Station at {host}:{port}"
        gateway = _api_gateway(host, port, scheduler)
    container = ServiceContainer(gateway, home, scheduler, backend_label=label, dumps_dir=dumps)
    return Application(qt_app, container, owns_qt_app=created), chosen


def _api_gateway(host: str, port: int, scheduler: QtScheduler) -> ApiStationGateway:
    """The JSON-RPC client, its callbacks posted to the GUI thread. It connects in the background: the app's
    first calls wait for the connection, and if the station can't be reached the app still opens and the client
    keeps retrying (the log says so)."""
    poster = QtPoster()   # the gateway holds poster.post, which keeps it alive
    gateway = ApiStationGateway(host, port, scheduler, poster.post)
    gateway.start()
    return gateway


def _parse(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sirat", description="SiRAT register access tool")
    parser.add_argument("--backend", choices=BACKENDS, default="fake",
                        help="fake: in-process fake; fake-tcp: the fake over TCP (JSON-RPC); api: a station service")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="happy",
                        help="fake backend scenario (fake and fake-tcp)")
    parser.add_argument("--host", default="127.0.0.1", help="station service host (api)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="station service port (api)")
    parser.add_argument("--home", type=Path, default=None, help="folder holding user settings")
    parser.add_argument("--no-demo-data", action="store_true", help="don't seed demo favorites/actions")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """The `sirat` command: parse arguments, set up logging, build and run the app. Returns the exit code."""
    args = _parse(sys.argv[1:] if argv is None else argv)
    log_path = setup_logging(getattr(logging, str(args.log_level).upper(), logging.INFO),
                             session_log_dir(), daily_log_dir())
    app, scenario = build_app(args.backend, args.scenario, args.home, not args.no_demo_data,
                              host=args.host, port=args.port)
    if log_path:
        logging.getLogger("SiRAT").info("Session log: %s", log_path)
    crash_guard.install(app.container.services.log, app.container.interactions)
    window = app.load()
    window.showMaximized()  # req 1: initial state maximized
    app.container.start(autoconnect=scenario.autoconnect, position=app.container.state.position)
    return app.exec()


def _start_viewer(log_level: int, scenario: str) -> Application:
    global _running
    setup_logging(log_level, session_log_dir(), daily_log_dir())
    app, chosen = build_app("fake", scenario)
    _running = app
    app.load()
    app.container.start(autoconnect=chosen.autoconnect)
    return app


# `parent` is unused; it keeps the call signature the old SiRAT launcher uses (req 1).
def launch_viewer(parent: object = None, log_level: int = logging.INFO, scenario: str = "happy") -> int:
    """Blocking launch from Python/PyCharm. A second call brings the existing window to front."""
    global _running
    if _running is not None:
        _running.bring_to_front()
        return 0
    app = _start_viewer(log_level, scenario)
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
    return _start_viewer(log_level, scenario)
