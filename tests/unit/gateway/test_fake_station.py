"""The fake must behave like the API contract, or the UI tests built on it would lie."""

from sirat_ui.gateway.models import LpwPhy
from sirat_ui.gateway.errors import ErrorCode
from sirat_ui.gateway.fake import FakeStationGateway
from sirat_ui.gateway.models import ActivityFinished, DutDisconnected, WatchValues
from sirat_ui.gateway.scheduler import ManualScheduler


def results(call):
    out = []
    call.then(lambda r: out.append(("ok", r)), lambda e: out.append(("err", e.code)))
    return out


def test_calls_fail_with_wrong_state_until_a_dut_is_connected():
    fake = FakeStationGateway(ManualScheduler())
    out = results(fake.read_register(1, "BUFC.LPMODE"))
    assert out == [("err", ErrorCode.WRONG_STATE)]


def test_critical_writes_need_confirm(fake):
    assert results(fake.write_register(1, "CMU.CLKEN0", 1)) == [("err", ErrorCode.CONFIRMATION_REQUIRED)]
    assert results(fake.write_register(1, "CMU.CLKEN0", 1, confirm=True))[0][0] == "ok"


def test_read_only_bits_make_verification_fail(fake):
    out = []
    fake.write_register(1, "BUFC.BUF0_CTRL", 0xFF).then(None, out.append)
    assert out[0].code == ErrorCode.VERIFY_FAILED
    assert out[0].data == {"written": 0xFF, "readback": 0x07}


def test_access_rules(fake):
    assert results(fake.read_register(1, "BUFC.BUF0_CMD")) == [("err", ErrorCode.ACCESS_DENIED)]
    assert results(fake.write_register(1, "BUFC.IPVERSION", 1)) == [("err", ErrorCode.ACCESS_DENIED)]
    assert results(fake.read_register(1, "NOPE.REG")) == [("err", ErrorCode.NOT_FOUND)]


def test_watch_refuses_read_sensitive_registers(fake):
    assert results(fake.watch(1, ["USART0.RXDATA"], 1.0)) == [("err", ErrorCode.READ_SENSITIVE)]


def test_watch_pushes_values_each_interval():
    scheduler = ManualScheduler()
    fake = FakeStationGateway(scheduler)
    fake.connect_dut(1)
    events = []
    fake.events.connect(lambda e: events.append(e) if isinstance(e, WatchValues) else None)
    fake.watch(1, ["SYNTH.FREQ"], 0.5)
    scheduler.advance(1000)
    assert len(events) == 2
    assert "SYNTH.FREQ" in events[0].values


def test_disconnect_clears_facts_and_emits_an_event(fake):
    events = []
    fake.events.connect(events.append)
    fake.load_phy(1, LpwPhy("BLE_1M"))
    fake.drop_dut(1, "power cycle")
    assert any(isinstance(e, DutDisconnected) for e in events)
    assert fake.facts[1].dut_connected is False and fake.facts[1].phy is None


def test_sequences_run_step_by_step_and_block_writes_while_running():
    scheduler = ManualScheduler()
    fake = FakeStationGateway(scheduler)
    fake.connect_dut(1)
    finished = []
    fake.events.connect(lambda e: finished.append(e) if isinstance(e, ActivityFinished) else None)
    fake.run_sequence(1, [{"register": "BUFC.LPMODE", "value": 0}, {"type": "dut_reconnect"}])
    assert results(fake.write_register(1, "BUFC.LPMODE", 1)) == [("err", ErrorCode.WRONG_STATE)]
    scheduler.run_pending()
    assert finished and finished[0].ok
    assert fake.memory.values["BUFC.LPMODE"] == 0


def test_abort_ends_a_sequence_as_aborted():
    scheduler = ManualScheduler()
    fake = FakeStationGateway(scheduler)
    fake.connect_dut(1)
    finished = []
    fake.events.connect(lambda e: finished.append(e) if isinstance(e, ActivityFinished) else None)
    activity = []
    fake.run_sequence(1, [{"type": "dut_reconnect"}] * 5).then(activity.append)
    scheduler.advance(500)
    fake.abort_sequence(activity[0])
    scheduler.run_pending()
    assert finished[0].ok is False and finished[0].error.code == ErrorCode.ABORTED


def test_held_calls_resolve_only_on_release(fake):
    fake.auto_resolve = False
    out = results(fake.read_register(1, "BUFC.EN"))
    assert out == []
    fake.release()
    assert out == [("ok", 1)]


def test_disconnect_and_recover_work(fake):
    assert results(fake.disconnect_dut(1))[0][0] == "ok"
    assert fake.facts[1].dut_connected is False
    assert results(fake.recover(1))[0][0] == "ok"



def test_connect_address_override_rules():
    fake = FakeStationGateway(ManualScheduler())
    assert results(fake.connect_dut(1, "EFR32", "", "  ", None)) == [("err", ErrorCode.INVALID_PARAMS)]
    assert results(fake.connect_dut(1, "EFR32", "", "h", 0)) == [("err", ErrorCode.INVALID_PARAMS)]
    assert results(fake.connect_dut(1, "EFR32", "", "10.255.255.1", 10001)) == [("err", ErrorCode.TIMEOUT)]
    assert results(fake.connect_dut(1, "EFR32", "", "192.168.1.5", None))[0][0] == "ok"
    info = []
    fake.dut_info(1).then(info.append)
    assert (info[0].rta["host"], info[0].rta["port"]) == ("192.168.1.5", 10001)
    fake.connect_dut(1)  # no override: back to the workspace config
    fake.dut_info(1).then(info.append)
    assert info[1].rta["host"] == "localhost"
