"""ApiStationGateway over TCP: what's the GUI's own on top of station_client.Link (gateway/api/client.py).

Replies decode into the app's models, events into GatewayEvents, a dropped link becomes DutDisconnected for each
connected position and a fresh status once it's back, and call.late is decoded with the method that timed out.
"""

from __future__ import annotations

import queue
import time
from typing import Any, Callable, List

import pytest

from sirat_ui.gateway.api.client import OPEN, ApiStationGateway
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ErrorCode
from sirat_ui.gateway.fake.fake_station import FakeStationGateway
from sirat_ui.gateway.fake.server import FakeStationServer
from sirat_ui.gateway.thread_scheduler import ThreadScheduler
from sirat_ui.models.station import CallLate, DutDisconnected, LogLine, LpwPhy, StatusChanged, WatchValues


class Gui:
    def __init__(self) -> None:
        self.server_clock = ThreadScheduler("api-station").start()
        self.client_clock = ThreadScheduler("api-client").start()
        self.fake = self.server_clock.run(lambda: FakeStationGateway(self.server_clock))
        self.server = FakeStationServer(self.fake, self.server_clock).start()
        self._posted: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.client = ApiStationGateway("127.0.0.1", self.server.address[1], self.client_clock, self._posted.put,
                                        retry_first_s=0.05, retry_max_s=0.2)
        self.events: List[Any] = []
        self.client.events.connect(self.events.append)
        self.client.open()
        self.result(self.client.subscribe(["status", "activity", "watch", "log"]))

    def pump(self, until: Callable[[], Any], timeout: float = 5.0) -> None:
        end = time.monotonic() + timeout
        while not until():
            if time.monotonic() > end:
                raise AssertionError("timed out waiting")
            try:
                self._posted.get(timeout=0.02)()
            except queue.Empty:
                pass

    def result(self, call: Call) -> Any:
        self.pump(lambda: not call.pending)
        if not call.ok:
            raise call.error   # type: ignore[misc]
        return call.result

    def error(self, call: Call) -> Any:
        self.pump(lambda: not call.pending)
        assert not call.ok
        return call.error

    def of(self, cls: type) -> List[Any]:
        return [e for e in self.events if isinstance(e, cls)]

    def logs(self) -> List[str]:
        return [e.text for e in self.of(LogLine) if e.source == "gateway"]

    def close(self) -> None:
        self.client.close()
        self.server.stop()
        errors = self.server_clock.errors + self.client_clock.errors
        self.server_clock.stop()
        self.client_clock.stop()
        assert errors == [], errors


@pytest.fixture
def gui():
    g = Gui()
    yield g
    g.close()


@pytest.fixture
def connected(gui):
    gui.result(gui.client.connect_dut(1, "EFR32", ""))
    return gui


def test_replies_decode_into_the_apps_models(connected):
    tree = connected.result(connected.client.register_tree(1))
    assert tree == connected.server_clock.run(lambda: connected.fake.peripherals)
    assert connected.result(connected.client.load_phy(1, LpwPhy("BLE_1M"))).name == "BLE_1M"
    assert connected.result(connected.client.write_register(1, "BUFC.LPMODE", 1)).value_written == 1
    assert connected.result(connected.client.read_register(1, "BUFC.LPMODE")) == 1
    assert connected.result(connected.client.hello())["release_id"] == "fake-2026.10"


def test_events_decode_into_gateway_events(connected):
    sub_id = connected.result(connected.client.watch(1, ["BUFC.LPMODE"], 0.1))
    connected.pump(lambda: any(e.sub_id == sub_id for e in connected.of(WatchValues)))
    assert connected.of(StatusChanged) and connected.of(LogLine)


def test_a_dropped_link_disconnects_each_dut_then_resyncs_the_status(connected):
    connected.result(connected.client.status())   # the client now knows DUT 1 is connected
    connected.server.drop_connections()
    connected.pump(lambda: connected.of(DutDisconnected))
    assert connected.of(DutDisconnected)[0].detected_by == "station connection"
    statuses = len(connected.of(StatusChanged))
    connected.pump(lambda: connected.client.state == OPEN and len(connected.of(StatusChanged)) > statuses)
    assert any("Reconnected" in text for text in connected.logs())
    assert connected.of(StatusChanged)[-1].status.positions[0].dut_connected   # the station kept the DUT


def test_call_late_is_decoded_with_the_method_that_timed_out(connected):
    connected.server_clock.run(lambda: connected.fake.time_out_next("registers.write", late_ms=200))
    error = connected.error(connected.client.write_register(1, "BUFC.LPMODE", 1))
    assert error.code == ErrorCode.TIMEOUT and error.data["still_running"] is True
    connected.pump(lambda: connected.of(CallLate))
    late = connected.of(CallLate)[0]
    assert late.request_id == error.data["request_id"] and late.ok and late.result.value_written == 1
