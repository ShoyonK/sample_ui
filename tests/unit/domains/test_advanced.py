"""Advanced page: custom functions (req 15), memory viewer (19), Python console (20), DUT control explorer (22)."""

import json

import pytest


def _texts(output_model, level=None):
    return [r["text"] for r in output_model.items if level is None or r["level"] == level]


# ---- Python console (req 20) --------------------------------------------------------------------------

@pytest.mark.req("20.exec")
def test_console_evaluates_executes_and_keeps_variables(harness):
    con = harness.shell.pyConsole
    for code in ("x = 21", "x * 2", "print('hello')", "1/0"):
        con.setDraft(code)
        con.execute()
    out = con.output.items
    assert ("input", ">>> x * 2") in [(r["level"], r["text"]) for r in out]
    assert "42" in _texts(con.output, "result")
    assert "hello" in _texts(con.output, "stdout")
    assert any("ZeroDivisionError: division by zero" in t for t in _texts(con.output, "error"))
    assert con.draft == "" and len(harness.fake.advanced.sessions) == 1


@pytest.mark.req("20.history")
def test_history_steps_back_and_forward_and_wraps(harness):
    con = harness.shell.pyConsole
    for code in ("a = 1", "b = 2", "b = 2"):     # repeats aren't stored twice
        con.setDraft(code)
        con.execute()
    con.historyPrevious()
    assert con.draft == "b = 2"
    con.historyPrevious()
    assert con.draft == "a = 1"
    con.historyPrevious()                         # wraps to the newest
    assert con.draft == "b = 2"
    con.historyNext()
    assert con.draft == "a = 1"


@pytest.mark.req("20.help")
def test_help_lists_the_namespace_instead_of_starting_interactive_help(harness):
    con = harness.shell.pyConsole
    con.setDraft("help")
    con.execute()
    text = "\n".join(_texts(con.output))
    assert "Available objects" in text and "dut" in text and "wait_ms" in text
    assert harness.fake.calls_to("advanced.console.exec") == []


@pytest.mark.req("20.session")
def test_disconnect_ends_the_session_and_says_so(harness):
    con = harness.shell.pyConsole
    con.setDraft("x = 1")
    con.execute()
    harness.fake.drop_dut(1)
    assert any("disconnected" in t for t in _texts(con.output, "note"))
    assert "isn't connected" in con.sessionText


@pytest.mark.req("20.session")
def test_a_session_that_vanished_on_the_station_is_reopened_once(harness):
    con = harness.shell.pyConsole
    con.setDraft("x = 1")
    con.execute()
    harness.fake.advanced.sessions.clear()                 # the station restarted, say
    con.setDraft("2 + 2")
    con.execute()
    assert "4" in _texts(con.output, "result")
    assert any("started a new one" in t for t in _texts(con.output, "note"))


@pytest.mark.req("20.restart")
def test_restart_clears_the_variables(harness):
    con = harness.shell.pyConsole
    con.setDraft("x = 1")
    con.execute()
    con.restart()
    con.setDraft("x")
    con.execute()
    assert any("NameError" in t for t in _texts(con.output, "error"))


def test_runaway_code_is_stopped(harness):
    harness.fake.advanced.exec_time_limit_s = 0.2
    con = harness.shell.pyConsole
    con.setDraft("while True: pass")
    con.execute()
    assert any("Stopped after 0.2 s" in t for t in _texts(con.output, "error"))


# ---- custom functions (req 15) -------------------------------------------------------------------------

@pytest.mark.req("15.persist")
def test_create_edit_and_persist_a_function(harness):
    fn = harness.shell.customFunctions
    harness.ix.answer_next({"name": "read_rssi"})
    fn.newFunction()
    assert fn.selectedName == "read_rssi" and "return rssi" in fn.code
    fn.setCode("return 7\n")
    saved = json.loads((harness.home / ".sirat_custom_functions.json").read_text())
    assert saved == [{"name": "read_rssi", "code": "return 7\n"}]
    assert harness.restart().shell.customFunctions.code == "return 7\n"


@pytest.mark.req("15.names")
def test_names_must_be_python_identifiers(harness):
    fn = harness.shell.customFunctions
    harness.ix.answer_next({"name": "2 bad"})
    fn.newFunction()
    assert fn.functions == [] and "letters, digits" in harness.ix.toasts[-1][1]


@pytest.mark.req("15.namespace")
def test_run_shares_variables_with_the_console_and_supports_return(harness):
    fn, con = harness.shell.customFunctions, harness.shell.pyConsole
    harness.ix.answer_next({"name": "read_rssi"})
    fn.newFunction()
    fn.run()
    assert "RSSI: -72 dBm" in _texts(fn.output, "stdout") and "-72" in _texts(fn.output, "result")
    assert any("result_read_rssi is set" in t for t in _texts(fn.output, "note"))
    con.setDraft("rssi, result_read_rssi, last_dut_api_result")
    con.execute()
    assert "(-72, -72, -72)" in _texts(con.output, "result")


@pytest.mark.req("15.actions")
def test_add_to_actions_and_run_it_in_a_sequence(harness):
    fn = harness.shell.customFunctions
    harness.ix.answer_next({"name": "set_ch"})
    fn.newFunction()
    fn.setCode("dut.dut_control.lpw.radio.SetChannel(7)\n")
    fn.addToActions()
    action = harness.services.actions.get("set_ch")
    assert action is not None and action.operations == [{"type": "custom_function", "function_name": "set_ch"}]
    harness.services.actions.run(["set_ch"])
    harness.scheduler.advance(2000)
    assert harness.fake.advanced.duts[1].state["channel"] == 7


def test_rename_and_delete(harness):
    fn = harness.shell.customFunctions
    harness.ix.answer_next({"name": "one"})
    fn.newFunction()
    harness.ix.answer_next({"name": "two"})
    fn.renameFunction()
    assert fn.functions == ["two"]
    harness.ix.answer_next(True)
    fn.deleteFunction()
    assert fn.functions == [] and not fn.hasSelection


def test_run_needs_a_connected_dut(disconnected):
    fn = disconnected.shell.customFunctions
    disconnected.ix.answer_next({"name": "f"})
    fn.newFunction()
    assert not fn.canRun and fn.runHint == "Connect a DUT to run functions"


# ---- DUT control explorer (req 22) -----------------------------------------------------------------------

def _select(dc, path):
    package, module, _ = path.split(".")
    dc.setFilter(path.split(".")[-1])
    keys = [r["key"] for r in dc.rows.items]
    dc.activate(keys.index(path))
    assert dc.selectedPath == path


@pytest.mark.req("22.tree")
def test_tree_browses_packages_modules_and_methods(harness):
    dc = harness.shell.dutControl
    dc.load()
    labels = [r["label"] for r in dc.rows.items]
    assert labels == ["Common", "Host", "LPW", "WiFi"]
    dc.activate(2)                                # LPW
    assert [r["label"] for r in dc.rows.items][3:5] == ["ble", "radio"]
    dc.activate(4)                                # radio
    assert "SetPower" in [r["label"] for r in dc.rows.items]
    dc.collapseAll()
    assert len(dc.rows.items) == 4


@pytest.mark.req("22.inspect")
def test_selecting_a_method_shows_signature_doc_and_defaults(harness):
    dc = harness.shell.dutControl
    dc.load()
    _select(dc, "lpw.radio.StartTx")
    assert dc.signature == "StartTx(num_packets: int = 0, continuous: bool = False) -> None"
    assert dc.doc.startswith("Start transmitting")
    params = dc.params.items
    assert [(p["name"], p["value"], p["isBool"]) for p in params] == [("num_packets", "0", False),
                                                                         ("continuous", "False", True)]


@pytest.mark.req("22.execute")
def test_execute_parses_parameters_and_shows_the_result(harness):
    dc = harness.shell.dutControl
    dc.load()
    _select(dc, "lpw.radio.SetPower")
    assert not dc.canExecute and dc.problemText == "power_dbm is required"
    dc.setParam("power_dbm", "10.5")
    dc.execute()
    assert harness.fake.calls_to("advanced.dut_control.invoke")[-1].params["kwargs"] == {"power_dbm": 10.5}
    assert "✓ Result (float): 10.5" in _texts(dc.output, "result")


@pytest.mark.req("22.hints")
def test_failures_come_with_a_hint(harness):
    dc = harness.shell.dutControl
    dc.load()
    _select(dc, "lpw.radio.SetPower")
    dc.setParam("power_dbm", "30")
    dc.execute()
    assert any("RAIL assert" in t for t in _texts(dc.output, "error"))
    assert any("Check the parameters" in t for t in _texts(dc.output, "hint"))
    _select(dc, "common.system.Delay")
    dc.setParam("ms", "9000")
    dc.execute()
    assert any("SetRpcTimeout" in t for t in _texts(dc.output, "hint"))


@pytest.mark.req("22.actions")
def test_add_to_actions_records_the_call(harness):
    dc = harness.shell.dutControl
    dc.load()
    _select(dc, "common.ble.StartAdvertising")
    dc.setParam("channel", "38")
    dc.addToActions()
    action = harness.services.actions.get("ble_StartAdvertising")
    assert action.operations == [{"type": "dut_control_method", "method_path": "common.ble.StartAdvertising",
                           "method_name": "StartAdvertising", "params": {"channel": 38}}]
    harness.services.actions.run(["ble_StartAdvertising"])
    harness.scheduler.advance(2000)
    assert harness.fake.advanced.duts[1].state["adv_channel"] == 38


def test_tree_is_dropped_on_disconnect(harness):
    dc = harness.shell.dutControl
    dc.load()
    harness.fake.drop_dut(1)
    assert dc.rows.items == [] and dc.treeText == "Connect a DUT to browse its control API"


# ---- memory viewer (req 19) ----------------------------------------------------------------------------------

@pytest.mark.req("19.read")
def test_read_shows_a_hex_dump_and_saves_the_address(harness):
    mem = harness.shell.memory
    assert mem.address == "0x20000000"
    mem.setField("address", "0x20000002")
    mem.setField("size", "32")
    mem.read()
    rows = mem.rows.items
    assert rows[0]["address"] == "0x20000000" and rows[0]["ascii"] == "SiRAT fake RAM.."
    assert [c["t"] for c in rows[0]["cells"]][:4] == ["53", "69", "52", "41"]
    assert "aligned from 0x20000002" in mem.headerText
    saved = json.loads((harness.home / ".sirat" / "memory_viewer.json").read_text())
    assert saved == {"last_address": "0x20000002"}
    assert harness.restart().shell.memory.address == "0x20000002"


@pytest.mark.req("19.format")
def test_words_and_dwords_are_little_endian(harness):
    mem = harness.shell.memory
    mem.setField("size", "32")
    mem.read()
    mem.setFormat(2)
    assert [c["t"] for c in mem.rows.items[0]["cells"]][:1] == ["0x41526953"]   # "SiRA"
    mem.setFormat(1)
    assert len(mem.rows.items[0]["cells"]) == 8


@pytest.mark.req("19.write")
def test_write_is_confirmed_then_shown_as_a_change(harness):
    mem = harness.shell.memory
    mem.setField("size", "64")
    mem.read()
    mem.setField("writeAddress", "0x20000004")
    mem.setField("writeValue", "0xAB")
    mem.setWriteSize(0)
    harness.ix.answer_next(False)
    mem.write()
    assert harness.fake.calls_to("memory.write") == []
    harness.ix.answer_next(True)
    mem.write()
    assert harness.ix.confirms[-1].message == "Write 0xAB to address 0x20000004?"
    cell = mem.rows.items[0]["cells"][4]
    assert cell == {"t": "AB", "c": True} and "changed since the last read" in mem.headerText


@pytest.mark.req("19.validate")
def test_bad_input_blocks_read_and_write(harness):
    mem = harness.shell.memory
    mem.setField("size", "5000")
    assert not mem.canRead and "1 to 4096" in mem.errors["size"]
    mem.setField("writeAddress", "0x20000002")
    mem.setField("writeValue", "0x1")
    assert not mem.canWrite and "inside one 4-byte word" in mem.errors["write"]   # DWord at offset 2


def test_flash_writes_are_refused_by_the_station(harness):
    mem = harness.shell.memory
    mem.setField("writeAddress", "0x08000000")
    mem.setField("writeValue", "1")
    harness.ix.answer_next(True)
    mem.write()
    assert "Flash can't be written" in harness.ix.toasts[-1][1]
