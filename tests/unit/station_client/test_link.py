"""station_client.Link keeps the link up: reconnecting, the heartbeat, requests made while connecting, and
subscribing again. The peer is this repository's fake station over TCP (gateway/fake/server.py)."""

from __future__ import annotations

import queue
import socket
import threading
import time
from typing import Any, Callable, List

import pytest

from station_client.link import CONNECTING, LOST, OPEN, OPENED, UNREACHABLE, WAITING, Link
from station_client.threads import ThreadScheduler
from station_protocol import jsonrpc
from station_protocol.errors import ErrorCode
from sibench_ui.gateway.fake.fake_station import FakeStationGateway
from sibench_ui.gateway.fake.server import FakeStationServer


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Harness:
    """A Link to a fake station that can be started late (`serve`) and dropped (`drop`)."""

    def __init__(self, listen: bool = True, port: int = 0, **options: Any) -> None:
        self.server_clock = ThreadScheduler("link-station").start()
        self.client_clock = ThreadScheduler("link-client").start()
        self.fake = self.server_clock.run(lambda: FakeStationGateway(self.server_clock))
        self.server = None
        self.port = port or _free_port()
        if listen:
            self.serve()
        self._posted: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.notes: List[Any] = []
        self.changes: List[Any] = []
        self.link = Link("127.0.0.1", self.port, self.client_clock, self._posted.put, "link-test",
                         lambda note, gap: self.notes.append(note), self.changes.append,
                         **{"retry_first_s": 0.05, "retry_max_s": 0.2, **options})

    def serve(self) -> None:
        self.server = FakeStationServer(self.fake, self.server_clock, port=self.port).start()

    def pump(self, until: Callable[[], Any], timeout: float = 5.0) -> None:
        end = time.monotonic() + timeout
        while not until():
            if time.monotonic() > end:
                raise AssertionError("timed out waiting")
            try:
                self._posted.get(timeout=0.02)()
            except queue.Empty:
                pass

    def send(self, method: str, **params: Any) -> List[Any]:
        box: List[Any] = []
        self.link.request(method, params, 5000, lambda raw, error: box.append((raw, error)))
        return box

    def wait(self, box: List[Any]) -> Any:
        self.pump(lambda: box)
        return box[0]

    def kinds(self) -> List[str]:
        return [c.kind for c in self.changes]

    def close(self) -> None:
        self.link.close()
        if self.server is not None:
            self.server.stop()
        errors = self.server_clock.errors + self.client_clock.errors
        self.server_clock.stop()
        self.client_clock.stop()
        assert errors == [], errors


@pytest.fixture
def make():
    made: List[Harness] = []

    def build(**options: Any) -> Harness:
        made.append(Harness(**options))
        return made[-1]
    yield build
    for h in made:
        h.close()


def test_a_dropped_link_fails_pending_requests_then_reconnects_and_subscribes_again(make):
    h = make()
    h.link.open()
    h.link.subscribe(["watch"], 5000, lambda *_: None)
    h.wait(h.send("dut.connect", pos=1, config_type="EFR32", config_file=""))
    h.server_clock.run(lambda: h.fake.set_latency("registers.read", 2000))
    pending = h.send("registers.read", pos=1, name="BUFC.LPMODE")
    h.server.drop_connections()
    _, error = h.wait(pending)
    assert error.code == ErrorCode.INTERNAL and "connection" in error.message.lower()
    h.pump(lambda: h.link.state == OPEN and OPENED in h.kinds()[h.kinds().index(LOST):])
    assert [c for c in h.changes if c.kind == OPENED][-1].reconnect
    h.server_clock.run(lambda: h.fake.set_latency("registers.read", 0))
    raw, _ = h.wait(h.send("registers.watch", pos=1, names=["BUFC.LPMODE"], interval_s=0.1))
    h.pump(lambda: any(n.method == "registers.watch" and n.data["sub_id"] == raw["sub_id"] for n in h.notes))


def test_a_station_that_starts_late_is_connected_to_when_it_comes_up(make):
    h = make(listen=False)
    h.link.start()
    _, error = h.wait(h.send("sys.status"))   # made while connecting: held, then failed when the attempt fails
    assert error.code == ErrorCode.INTERNAL and "Can't reach the station" in error.message
    h.pump(lambda: h.link.state == WAITING)
    _, error = h.wait(h.send("sys.status"))   # while waiting: fails at once
    assert error.code == ErrorCode.INTERNAL
    h.serve()
    h.pump(lambda: h.link.state == OPEN)
    raw, error = h.wait(h.send("sys.status"))
    assert error is None and raw["release_id"]
    assert h.kinds().count(UNREACHABLE) == 1   # said once, not on every retry


def test_requests_made_while_connecting_are_sent_once_the_link_is_up(make):
    h = make()
    h.link.start()
    assert h.link.state == CONNECTING
    raw, error = h.wait(h.send("sys.status"))
    assert error is None and raw["release_id"]


def test_close_stops_retrying(make):
    h = make(listen=False)
    h.link.start()
    h.pump(lambda: h.link.state == WAITING)
    h.link.close()
    h.serve()
    _, error = h.wait(h.send("sys.status"))
    assert error.code == ErrorCode.INTERNAL


def test_a_station_that_stops_answering_is_found_by_the_heartbeat(make):
    """A server that accepts the connection and reads, but never answers."""
    silent = socket.socket()
    silent.bind(("127.0.0.1", 0))
    silent.listen()
    accepted = []

    def accept():
        conn, _ = silent.accept()
        accepted.append(conn)
        try:
            while conn.recv(65536):
                pass
        except OSError:
            pass
    threading.Thread(target=accept, daemon=True).start()
    h = make(listen=False, port=silent.getsockname()[1], heartbeat_s=0.3, heartbeat_timeout_ms=500)
    h.link.start()
    try:
        h.pump(lambda: h.link.state == OPEN)
        h.pump(lambda: any(c.kind == LOST and "stopped answering" in c.reason for c in h.changes), timeout=8)
    finally:
        for conn in accepted:
            conn.close()
        silent.close()


def test_a_seq_gap_is_reported():
    clock = ThreadScheduler("link-gap").start()
    seen: List[bool] = []
    link = Link("127.0.0.1", 1, clock, lambda fn: fn(), "link-test", lambda note, gap: seen.append(gap),
                lambda change: None)
    try:
        for seq in (1, 2, 5):
            link._notified(jsonrpc.Notification("log.line", seq, {}))   # what the connection hands the link
        assert seen == [False, False, True]
    finally:
        link.close()
        clock.stop()
