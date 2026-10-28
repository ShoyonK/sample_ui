"""A hardware error during a run faults the DUT position; Recover (sys.recover) clears it (API doc "Activities")."""

FAILING = [{"type": "dut_control_method", "method_path": "lpw.radio.SetPower", "method_name": "SetPower",
            "params": {"power_dbm": 30}}]          # out of range: the fake DUT raises a RAIL assert
HARMLESS = [{"register": "BUFC.LPMODE", "value": 1}]


def run(harness, ops):
    action = harness.services.actions.add("fault_test", ops)   # add() returns the unique name it used
    harness.services.actions.run([action.name])
    harness.scheduler.advance(2000)


def fault(harness):
    run(harness, FAILING)


def test_a_hardware_error_during_a_run_faults_the_position(harness):
    fault(harness)
    vm = harness.shell.faultRecovery
    assert vm.hasFault and "RAIL assert" in vm.faultText and vm.faultText.startswith("DUT 1 fault:")
    assert harness.shell.state.connectionText == "Fault"


def test_runs_are_refused_while_faulted_and_the_message_points_at_recover(harness):
    fault(harness)
    run(harness, HARMLESS)
    level, text = harness.ix.toasts[-1]
    assert level == "error" and "Recover" in text


def test_recover_asks_first_and_clears_the_fault(harness):
    fault(harness)
    vm = harness.shell.faultRecovery
    harness.ix.answer_next(False)
    vm.recover()
    assert harness.fake.calls_to("sys.recover") == [] and vm.hasFault
    assert harness.ix.confirms[-1].title == "Recover DUT 1?"

    harness.ix.answer_next(True)
    vm.recover()
    assert harness.fake.calls_to("sys.recover")[-1].params == {"pos": 1}
    assert not vm.hasFault and harness.ix.toasts[-1] == ("success", "DUT 1 recovered")

    run(harness, HARMLESS)
    assert harness.fake.memory.values["BUFC.LPMODE"] == 1      # runs work again


def test_no_fault_means_nothing_to_recover(harness):
    vm = harness.shell.faultRecovery
    assert not vm.hasFault and vm.faultText == ""
    vm.recover()
    assert harness.ix.confirms == [] and harness.fake.calls_to("sys.recover") == []
