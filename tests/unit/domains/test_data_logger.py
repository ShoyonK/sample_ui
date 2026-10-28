"""Data logger (req 17): rate range, watch vs polling, plots' shared zoom, status."""

import json

import pytest

from sirat_ui.gateway.errors import ErrorCode


def logger(h):
    return h.services.logger


@pytest.mark.req("17.rate")
def test_rates_inside_the_watch_range_use_a_station_watch(harness):
    harness.shell.logger.setRateText("1")
    harness.shell.logger.toggleRecording()
    assert logger(harness).mode == "watch"
    assert harness.fake.calls_to("registers.watch")[-1].params["interval_s"] == 1.0
    harness.scheduler.advance(3000)
    assert harness.shell.logger.sampleCount == 3


@pytest.mark.req("17.rate")
def test_fast_rates_poll_because_watch_stops_at_0_1_s(harness):
    harness.shell.logger.setRateText("0.01")
    harness.shell.logger.toggleRecording()
    assert logger(harness).mode == "polling"
    assert harness.fake.calls_to("registers.watch") == []
    harness.scheduler.advance(100)
    assert harness.shell.logger.sampleCount == 10
    assert "polling" in harness.shell.logger.modeText


@pytest.mark.req("17.rate")
def test_slow_rates_poll_because_watch_stops_at_60_s(harness):
    harness.shell.logger.setRateText("120")
    harness.shell.logger.toggleRecording()
    harness.scheduler.advance(360_000)
    assert harness.shell.logger.sampleCount == 3
    assert harness.fake.calls_to("registers.watch") == []


@pytest.mark.parametrize("text", ["0.001", "4000", "fast"])
def test_rates_outside_0_01_to_3600_are_rejected(harness, text):
    harness.shell.logger.setRateText(text)
    assert "between 0.01 and 3600" in harness.ix.toasts[-1][1]
    assert harness.shell.logger.rateText == "0.5"


def test_changing_the_rate_while_recording_switches_source(harness):
    harness.shell.logger.toggleRecording()
    assert logger(harness).mode == "watch"
    harness.shell.logger.setRateText("0.05")
    assert logger(harness).mode == "polling" and harness.shell.logger.recording
    assert harness.fake.calls_to("registers.unwatch")


def test_polling_stops_with_one_message_when_the_dut_is_gone(harness):
    harness.shell.logger.setRateText("0.01")
    harness.shell.logger.toggleRecording()
    harness.fake.fail_next("registers.read_many", ErrorCode.TIMEOUT)
    harness.scheduler.advance(100)
    assert harness.shell.logger.recording is False
    assert len([t for t in harness.ix.toasts if t[0] == "error"]) == 1


@pytest.mark.req("17.persist")
def test_rate_and_fields_persist_in_the_original_file(harness):
    harness.shell.logger.setRateText("0.25")
    harness.shell.logger.remove(0)
    saved = json.loads((harness.home / ".sirat_data_logger.json").read_text())
    assert saved == {"tracked_fields": ["AGC.RSSI.RSSI"], "sample_rate": 0.25}
    harness.shell.logger.remove(0)
    restarted = harness.restart()
    assert restarted.shell.logger.fieldCount == 0 and restarted.shell.logger.rateText == "0.25"


@pytest.mark.req("17.plots")
def test_each_series_has_sample_numbers_for_its_plot(harness):
    harness.shell.logger.toggleRecording()
    harness.scheduler.advance(2000)
    row = harness.shell.logger.series.items[0]
    assert row["samples"] == [0, 1, 2, 3]
    assert len(row["points"]) == 4
    assert "4 samples" in harness.shell.logger.statusText and "elapsed" in harness.shell.logger.statusText


@pytest.mark.req("17.zoom")
def test_zoom_is_shared_by_all_plots_and_resets(harness):
    vm = harness.shell.logger
    vm.zoomTo(8, 2)
    assert (vm.zoomStart, vm.zoomEnd) == (2, 8)
    vm.zoomTo(3, 3.4)  # a click, not a drag: ignored
    assert (vm.zoomStart, vm.zoomEnd) == (2, 8)
    vm.resetZoom()
    assert (vm.zoomStart, vm.zoomEnd) == (-1, -1)


def test_clear_resets_samples_and_zoom(harness):
    vm = harness.shell.logger
    vm.toggleRecording()
    harness.scheduler.advance(1000)
    vm.zoomTo(0, 1)
    vm.clear()
    assert vm.sampleCount == 0 and vm.zoomStart == -1
    assert all(r["points"] == [] for r in vm.series.items)
