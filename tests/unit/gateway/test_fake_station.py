"""The fake must behave like the API contract, or the UI tests built on it would lie."""

from sirat_ui.gateway.errors import ErrorCode
from sirat_ui.gateway.fake import FakeStationGateway
from sirat_ui.gateway.scheduler import ManualScheduler
from sirat_ui.models.station import ActivityFinished, DutDisconnected, WatchValues
from sirat_ui.models.station import CallLate, LpwPhy, RpcAddress


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
    """The write happened, so it's a result with verified=False, not an error (API design 6, registers)."""
    out = []
    fake.write_register(1, "BUFC.BUF0_CTRL", 0xFF).then(out.append)
    assert (out[0].written, out[0].readback, out[0].verified) == (0xFF, 0x07, False)


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
    fake.abort_activity(activity[0])
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
    assert results(fake.connect_dut(1, "EFR32", "", RpcAddress("  ", 10001))) == [("err", ErrorCode.INVALID_PARAMS)]
    assert results(fake.connect_dut(1, "EFR32", "", RpcAddress("h", 0))) == [("err", ErrorCode.INVALID_PARAMS)]
    assert results(fake.connect_dut(1, "EFR32", "", RpcAddress("10.255.255.1", 10001))) == \
        [("err", ErrorCode.TIMEOUT)]
    assert results(fake.connect_dut(1, "EFR32", "", RpcAddress("192.168.1.5", 10001)))[0][0] == "ok"
    info = []
    fake.dut_info(1).then(info.append)
    assert (info[0].rta["host"], info[0].rta["port"]) == ("192.168.1.5", 10001)
    fake.connect_dut(1)  # no override: back to the workspace config
    fake.dut_info(1).then(info.append)
    assert info[1].rta["host"] == "localhost"


def test_reconnect_is_rpc_only_and_needs_an_earlier_connect():
    fake = FakeStationGateway(ManualScheduler())
    assert results(fake.reconnect_dut(1)) == [("err", ErrorCode.NOT_FOUND)]
    fake.connect_dut(1)
    fake.drop_dut(1)
    assert results(fake.reconnect_dut(1))[0][0] == "ok" and fake.facts[1].dut_connected


def test_probe_never_touches_the_connection():
    fake = FakeStationGateway(ManualScheduler())
    fake.connect_dut(1)
    ok, missing = [], []
    fake.probe(1, None, 5).then(ok.append)
    fake.probe(1, RpcAddress("10.255.255.1", 10001), 5).then(missing.append)
    assert ok[0].ok and "localhost:10001" in ok[0].detail
    assert not missing[0].ok and "within 5 s" in missing[0].detail
    assert fake.facts[1].dut_connected  # still connected


def test_a_timed_out_call_finishes_late_and_says_so():
    scheduler = ManualScheduler()
    fake = FakeStationGateway(scheduler)
    fake.connect_dut(1)
    late = []
    fake.events.connect(lambda e: late.append(e) if isinstance(e, CallLate) else None)
    fake.time_out_next("registers.write", late_ms=1000)
    errors = []
    fake.write_register(1, "BUFC.LPMODE", 3).then(None, errors.append)
    assert errors[0].code == ErrorCode.TIMEOUT and errors[0].data["still_running"]
    assert fake.memory.values["BUFC.LPMODE"] != 3 and late == []
    scheduler.advance(1000)
    assert late[0].ok and late[0].request_id == errors[0].data["request_id"]
    assert fake.memory.values["BUFC.LPMODE"] == 3  # the write did happen


def test_read_sensitive_registers_need_an_opt_in_for_bulk_reads():
    fake = FakeStationGateway(ManualScheduler())
    fake.connect_dut(1)
    plain, opted = [], []
    fake.read_many(1, ["USART0.RXDATA"]).then(plain.append)
    fake.read_many(1, ["USART0.RXDATA"], include_read_sensitive=True).then(opted.append)
    assert plain[0][0].error.code == ErrorCode.READ_SENSITIVE
    assert opted[0][0].error is None


def test_status_carries_instrument_facts():
    fake = FakeStationGateway(ManualScheduler())
    kinds = {i.kind for i in fake.status_snapshot().instruments if i.connected}
    assert kinds == {"signal_generator", "rf_switch", "chamber", "eca"}
    fake.drop_instrument("switch1")
    assert not next(i for i in fake.status_snapshot().instruments if i.id == "switch1").connected
