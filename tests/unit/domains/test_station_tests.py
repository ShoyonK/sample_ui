"""Req 33 test execution, through the Tests page ViewModel against the fake station."""

import json

import pytest

from sibench_ui.gateway.errors import ErrorCode


def page(h):
    vm = h.shell.stationTests
    vm.ensureLoaded()
    return vm


def check(vm, *names):
    for name in names:
        vm.toggle(next(i for i, r in enumerate(vm.catalogue.items) if r["name"] == name))


def results(vm):
    return [(r["name"], r["status"]) for r in vm.results.items]


@pytest.mark.req("33.select")
def test_the_tests_are_listed_and_nothing_runs_until_some_are_checked(harness):
    vm = page(harness)
    assert [r["name"] for r in vm.catalogue.items] == ["Sample test 1", "Sample test 2", "Sample test 3",
                                                       "Sample test 4"]
    assert vm.checkedCount == 0 and not vm.canRun
    check(vm, "Sample test 2")
    assert vm.checkedCount == 1 and vm.canRun
    check(vm, "Sample test 2")
    assert vm.checkedCount == 0


@pytest.mark.req("33.run")
def test_a_run_shows_the_current_test_progress_and_each_result_as_it_ends(harness):
    vm = page(harness)
    check(vm, "Sample test 1", "Sample test 2")
    vm.run()
    assert vm.running and harness.fake.calls_to("tests.run")[-1].params["test_ids"] == ["sample_test_1",
                                                                                         "sample_test_2"]
    harness.scheduler.advance(150)
    assert vm.currentText == "Current test: Sample test 1" and vm.statusText == "Running · test 1 of 2"
    assert results(vm) == [] and vm.progress == 0.0
    harness.scheduler.advance(600)
    assert results(vm) == [("Sample test 1", "Pass")] and vm.progress == 0.5
    row = vm.results.items[0]
    assert row["durationText"] == "0.6 s" and row["startedText"] != "" and row["notes"] == ""
    harness.scheduler.run_pending()
    assert not vm.running and vm.progress == 1.0 and vm.currentText == ""
    assert vm.statusText == "Finished · 2 passed, 0 failed" and vm.verdict == "pass"


@pytest.mark.req("33.results")
def test_a_failure_shows_fail_with_its_note(harness):
    vm = page(harness)
    check(vm, "Sample test 3")
    vm.run()
    harness.scheduler.run_pending()
    assert results(vm) == [("Sample test 3", "Fail")]
    assert vm.results.items[0]["notes"] == "AssertionError: sample failure"
    assert vm.statusText == "Finished · 0 passed, 1 failed" and vm.verdict == "fail"


@pytest.mark.req("33.output")
def test_selecting_a_result_shows_what_that_test_printed(harness):
    vm = page(harness)
    check(vm, "Sample test 1", "Sample test 3")
    vm.run()
    harness.scheduler.run_pending()
    assert vm.outputTitle == "Output" and vm.output.items == []
    vm.selectResult(1)
    assert vm.outputTitle == "Output · Sample test 3" and vm.results.items[1]["selected"]
    assert [line["text"] for line in vm.output.items] == ["sample_test_3: started", "AssertionError: sample failure"]


@pytest.mark.req("33.stop")
def test_stop_ends_the_run_and_keeps_the_results_so_far(harness):
    vm = page(harness)
    check(vm, "Sample test 1", "Sample test 2")
    vm.run()
    harness.scheduler.advance(800)
    vm.stop()
    assert vm.currentText == "Stopping…"
    harness.scheduler.run_pending()
    assert results(vm) == [("Sample test 1", "Pass")]
    assert vm.statusText == "Stopped · 1 passed, 0 failed" and vm.currentText == "Stopped by user" and vm.canRun


def test_losing_the_dut_ends_the_run_and_says_so(harness):
    vm = page(harness)
    check(vm, "Sample test 1", "Sample test 2")
    vm.run()
    harness.scheduler.advance(800)
    harness.fake.drop_dut(1)
    harness.scheduler.run_pending()
    assert not vm.running and vm.currentText == "DUT 1 disconnected" and results(vm) == [("Sample test 1", "Pass")]


def test_running_needs_a_connected_dut(disconnected):
    vm = page(disconnected)
    check(vm, "Sample test 1")
    assert not vm.canRun
    vm.run()
    assert not disconnected.fake.calls_to("tests.run")


def test_the_selection_is_locked_while_running(harness):
    vm = page(harness)
    check(vm, "Sample test 1")
    vm.run()
    check(vm, "Sample test 2")
    assert vm.checkedCount == 1


def test_a_station_that_cannot_list_tests_says_so(harness):
    harness.fake.fail_next("tests.list", ErrorCode.INTERNAL, "Test folder missing")
    vm = page(harness)
    assert vm.emptyText == "Couldn't list the tests: Test folder missing"


@pytest.mark.req("33.export")
def test_export_writes_json_with_timestamps_status_and_output(harness, tmp_path):
    vm = page(harness)
    check(vm, "Sample test 1", "Sample test 3")
    vm.run()
    harness.scheduler.run_pending()
    target = tmp_path / "results.json"
    harness.ix.answer_save(str(target))
    vm.exportResults()
    assert harness.ix.save_requests[-1][1].startswith("sibench_tests_")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["started"] and data["finished"] and data["dut_position"] == 1
    assert [(t["id"], t["status"]) for t in data["tests"]] == [("sample_test_1", "pass"), ("sample_test_3", "fail")]
    failed = data["tests"][1]
    assert failed["notes"] == "AssertionError: sample failure" and failed["duration_s"] == 0.7 and failed["started"]
    assert failed["output"] == ["sample_test_3: started", "AssertionError: sample failure"]
    assert harness.ix.toasts[-1] == ("success", f"Saved results to {target}")
