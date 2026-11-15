"""The Station API contract, tested over a real TCP socket with the shared client (docs/STATION_API.md).

Each test talks to a station through station_client.Link and checks every reply and every event against
station_protocol's types: a result or event that doesn't fit fails the test. Nothing here uses the GUI.

By default each test starts this repository's fake station behind FakeStationServer. Set SIBENCH_STATION=host:port
to run the same tests against another station service instead (the backend's conformance run,
docs/BACKEND_GUIDE.md):

    SIBENCH_STATION=127.0.0.1:47800 uv run pytest tests/contract

Against another station, tests that need the fake's test knobs (forcing a timeout, dropping a DUT, looking inside
the station) skip with the reason. The tests assume the reference fixture the fake carries: a LION chip with
BUFC.LPMODE, instruments siggen1, switch1, chamber1 and eca1, the RF path TX_PATH and the sample tests. A station
under test should run in its simulation mode seeded with that fixture.

The link's callbacks are posted to a queue that the test thread runs (`Station.pump`). The only code tied to this
repository is under "the local station" below; in the station's repository it starts the service's simulation
mode instead, and the knobs call that mode's own.
"""

from __future__ import annotations

import os
import queue
import time
from typing import Any, Callable, List, Optional, Tuple

import pytest

from station_client.link import OPEN, Link, LinkChange
from station_client.threads import ThreadScheduler
from station_protocol import jsonrpc
from station_protocol.catalog import BY_EVENT, BY_WIRE, TOPICS
from station_protocol.errors import ApiError
from station_protocol.method import read_result
from station_protocol.validate import ValidationFailed, validate

TIMEOUT_MS = 5000


def _external() -> Optional[Tuple[str, int]]:
    value = os.environ.get("SIBENCH_STATION", "").strip()
    if not value:
        return None
    host, _, port = value.rpartition(":")
    return host or "127.0.0.1", int(port)


EXTERNAL = _external()
FAKE_ONLY = "needs the fake station's test knobs; runs only without SIBENCH_STATION"


# ---- the local station (this repository's fake) ---------------------------------------------------------------

class LocalStation:
    """The fake station on its own thread, behind a TCP server on a free port."""

    def __init__(self) -> None:
        from sibench_ui.gateway.fake.fake_station import FakeStationGateway
        from sibench_ui.gateway.fake.server import FakeStationServer
        self.clock = ThreadScheduler("contract-station").start()
        self.fake = self.clock.run(lambda: FakeStationGateway(self.clock))
        self.server = FakeStationServer(self.fake, self.clock).start()

    @property
    def address(self) -> Tuple[str, int]:
        return self.server.address

    def run(self, fn: Callable[[Any], Any]) -> Any:
        """fn(fake) on the fake's thread."""
        return self.clock.run(lambda: fn(self.fake))

    def close(self) -> List[BaseException]:
        self.server.stop()
        self.clock.stop()
        return self.clock.errors


# ---- a client session -----------------------------------------------------------------------------------------

class Station:
    """One client connection. `subscribe=False` leaves it unsubscribed."""

    def __init__(self, subscribe: bool = True) -> None:
        self.local = None if EXTERNAL else LocalStation()
        host, port = EXTERNAL or self.local.address   # type: ignore[union-attr]
        self.clock = ThreadScheduler("contract-client").start()
        self._posted: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.events: List[Tuple[str, Any]] = []        # (event name, validated data), in arrival order
        self.bad: List[str] = []                       # events that didn't fit the protocol
        self.changes: List[LinkChange] = []
        self.link = Link(host, port, self.clock, self._posted.put, "conformance", self._note, self.changes.append,
                         retry_first_s=0.05, retry_max_s=0.2)
        self.link.open()
        if subscribe:
            self.subscribe(list(TOPICS))

    @property
    def address(self) -> Tuple[str, int]:
        return self.link.host, self.link.port

    def _note(self, note: jsonrpc.Notification, gap: bool) -> None:
        event = BY_EVENT.get(note.method)
        if event is None:
            self.bad.append(f"unknown event {note.method}")
            return
        try:
            self.events.append((note.method, validate(event.data, note.data, note.method)))
        except ValidationFailed as exc:
            self.bad.append(str(exc))

    def pump(self, until: Callable[[], Any], timeout: float = 5.0) -> None:
        """Runs posted callbacks on this thread until `until()` is true."""
        end = time.monotonic() + timeout
        while not until():
            if time.monotonic() > end:
                raise AssertionError("timed out waiting")
            try:
                self._posted.get(timeout=0.02)()
            except queue.Empty:
                pass

    def send(self, method: str, timeout_ms: int = TIMEOUT_MS, **params: Any) -> List[Any]:
        """Sends a request; the returned box gets (raw result, error) when the reply comes."""
        box: List[Any] = []
        self.link.request(method, params, timeout_ms, lambda raw, error: box.append((raw, error)))
        return box

    def wait(self, method: str, box: List[Any], timeout: float = 5.0) -> Any:
        """The reply in `box`, checked against the method's result type; raises its ApiError."""
        self.pump(lambda: box, timeout)
        raw, error = box[0]
        if error is not None:
            raise error
        try:
            return read_result(BY_WIRE[method], raw)
        except ValidationFailed as exc:
            raise AssertionError(f"{method}'s result doesn't fit the protocol: {exc}") from None

    def call(self, method: str, **params: Any) -> Any:
        """The method's result, validated as its protocol type (a dataclass, a TypedDict...); raises its
        ApiError."""
        return self.wait(method, self.send(method, **params))

    def error(self, method: str, **params: Any) -> ApiError:
        box = self.send(method, **params)
        self.pump(lambda: box)
        raw, error = box[0]
        assert error is not None, f"expected an error from {method}, got {raw!r}"
        return error

    def subscribe(self, topics: List[str]) -> None:
        box: List[Any] = []
        self.link.subscribe(topics, TIMEOUT_MS, lambda raw, error: box.append((raw, error)))
        self.wait("sys.subscribe", box)

    def of(self, name: str) -> List[Any]:
        """The data of every `name` event so far."""
        return [data for event, data in self.events if event == name]

    def on_fake(self, fn: Callable[[Any], Any]) -> Any:
        """Runs fn(fake) on the fake's thread: a test knob, or a look inside. Skips against another station."""
        if self.local is None:
            pytest.skip(FAKE_ONLY)
        return self.local.run(fn)

    def drop_link(self) -> None:
        """The station closes every connection (fake only)."""
        if self.local is None:
            pytest.skip(FAKE_ONLY)
        self.local.server.drop_connections()

    def close(self) -> None:
        self.link.close()
        errors = self.clock.errors + (self.local.close() if self.local is not None else [])
        self.clock.stop()
        assert errors == [], errors
        assert self.bad == [], f"events that don't fit the protocol: {self.bad}"


@pytest.fixture
def make_station():
    """Builds Stations; closes them all afterwards."""
    made: List[Station] = []

    def make(**options: Any) -> Station:
        made.append(Station(**options))
        return made[-1]
    yield make
    for s in made:
        s.close()


def _clean(station: Station) -> None:
    """Another station lives on between tests, so each test starts with DUT 1 disconnected."""
    if EXTERNAL and station.link.state == OPEN:
        try:
            station.call("dut.disconnect", pos=1)
        except ApiError:
            pass


@pytest.fixture
def station(make_station):
    s = make_station()
    _clean(s)
    return s


@pytest.fixture
def connected(station):
    """A station with DUT 1 connected (disconnected again afterwards, so another station is left clean)."""
    station.call("dut.connect", pos=1, config_type="EFR32", config_file="")
    yield station
    _clean(station)
