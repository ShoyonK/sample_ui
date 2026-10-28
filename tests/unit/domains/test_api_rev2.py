"""Behavior the revised Station API contract brings (docs/API_DESIGN.md, revision 2)."""

from sirat_ui.gateway.errors import ErrorCode


def test_a_write_that_times_out_says_it_is_still_running_then_logs_the_outcome(harness):
    harness.select("BUFC.LPMODE")
    harness.fake.time_out_next("registers.write", late_ms=1500)
    harness.shell.detail.write("0x3")
    assert "still running" in harness.ix.toasts[-1][1]
    harness.scheduler.advance(1500)
    lines = [line.text for line in harness.services.log.lines]
    assert any("finished after all" in text for text in lines)
    assert harness.fake.memory.values["BUFC.LPMODE"] == 3


def test_a_custom_function_runs_with_its_code_from_the_users_file(harness):
    harness.container.stores.custom_functions.save([{"name": "init_ble", "code": "print('hi')"}])
    actions = harness.services.actions
    actions.add("ble_init", [{"type": "custom_function", "function_name": "init_ble"}])
    actions.run(["ble_init"])
    op = harness.fake.calls_to("automation.seq.run")[-1].params["ops"][0]
    assert op == {"type": "custom_function", "function_name": "init_ble", "code": "print('hi')", "group": "ble_init"}


def test_a_custom_function_without_code_is_refused_before_anything_runs(harness):
    actions = harness.services.actions
    actions.add("broken", [{"type": "custom_function", "function_name": "gone"}])
    failed = []
    actions.run(["broken"]).then(None, failed.append)
    assert failed[0].code == ErrorCode.INVALID_PARAMS and "gone" in failed[0].message
    assert harness.fake.calls_to("automation.seq.run") == []


def test_a_nested_sequence_op_is_expanded_into_its_actions(harness):
    actions = harness.services.actions
    actions.add("outer", [{"type": "sequence", "sequence_name": "s", "action_names": ["lpmode_on"]}])
    actions.run(["outer"])
    ops = harness.fake.calls_to("automation.seq.run")[-1].params["ops"]
    assert [(o["type"], o["group"]) for o in ops] == [("register_write", "lpmode_on")]
