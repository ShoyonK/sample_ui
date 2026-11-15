"""Tests page (req 33): select tests, run them, follow progress, read each result's output, export."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional, Set, Tuple

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.station_tests.service import StationTestService, TestResult, TestRun
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, ConsoleModel, DictListModel, clock_text, qprop
from sirat_ui.state.station import StationState


def _minutes(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


class StationTestsViewModel(BaseViewModel):
    """The Tests page: the checklist, Run/Stop, progress, results, the selected result's output, Export."""

    changed = pyqtSignal()

    def __init__(self, tests: StationTestService, state: StationState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tests = tests
        self._state = state
        self._interactions = interactions
        self._catalogue = DictListModel(["id", "name", "checked"], self)
        self._results = DictListModel(["num", "id", "name", "status", "durationText", "notes", "startedText",
                                       "selected"], self)
        self._output = ConsoleModel(self)
        self._checked: Set[str] = set()
        self._selected_result = -1
        self._running = False
        self._has_run = False
        self._progress = 0.0
        self._status_text = ""
        self._verdict = ""
        self._current_text = ""
        self._elapsed_text = ""
        self._checked_count = 0
        self._can_run = False
        self._output_title = "Output"
        self._empty_text = ""
        tests.changed.connect(self._rebuild)
        tests.progress.connect(self._rebuild)
        state.changed.connect(self._rebuild)
        self._rebuild()

    running = qprop(bool, "_running", changed)
    hasRun = qprop(bool, "_has_run", changed)
    progress = qprop(float, "_progress", changed)
    statusText = qprop(str, "_status_text", changed)
    verdict = qprop(str, "_verdict", changed)            # "" | running | pass | fail | stopped
    currentText = qprop(str, "_current_text", changed)
    elapsedText = qprop(str, "_elapsed_text", changed)
    checkedCount = qprop(int, "_checked_count", changed)
    canRun = qprop(bool, "_can_run", changed)
    selectedResult = qprop(int, "_selected_result", changed)
    outputTitle = qprop(str, "_output_title", changed)
    emptyText = qprop(str, "_empty_text", changed)

    @pyqtProperty(QObject, constant=True)
    def catalogue(self) -> DictListModel:
        return self._catalogue

    @pyqtProperty(QObject, constant=True)
    def results(self) -> DictListModel:
        return self._results

    @pyqtProperty(QObject, constant=True)
    def output(self) -> ConsoleModel:
        return self._output

    @pyqtSlot()
    def ensureLoaded(self) -> None:  # noqa: N802
        """The page calls this when it first shows."""
        if not self._tests.loaded:
            self._tests.load()

    @pyqtSlot(int)
    def toggle(self, row: int) -> None:
        item = self._catalogue.get(row)
        if item and not self._running:
            self._checked ^= {item["id"]}
            self._rebuild()

    @pyqtSlot()
    def run(self) -> None:
        if self._can_run:
            self._selected_result = -1
            self._tests.start(sorted(self._checked))

    @pyqtSlot()
    def stop(self) -> None:
        self._tests.stop()

    @pyqtSlot(int)
    def selectResult(self, row: int) -> None:  # noqa: N802
        self._selected_result = row
        self._rebuild()

    @pyqtSlot()
    def exportResults(self) -> None:  # noqa: N802
        run = self._tests.run
        if run is None:
            return

        def chosen(path: Optional[str]) -> None:
            if not path:
                return
            try:
                self._tests.export(Path(path))
                self._interactions.toast("success", f"Saved results to {path}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save: {exc}")

        suggested = time.strftime("sirat_tests_%Y%m%d_%H%M%S.json", time.localtime(run.started))
        self._interactions.choose_save_file("Export test results", suggested, "JSON files (*.json)").then(chosen)

    def _rebuild(self) -> None:
        self._catalogue.set_items([{"id": t.id, "name": t.name, "checked": t.id in self._checked}
                                   for t in self._tests.tests])
        run = self._tests.run
        results = run.results if run is not None else []
        if self._selected_result >= len(results):
            self._selected_result = -1
        self._results.set_items([
            {"num": f"{i + 1:02d}", "id": r.test.id, "name": r.test.name, "status": "Pass" if r.passed else "Fail",
             "durationText": f"{r.duration_s:.1f} s", "notes": r.notes, "startedText": clock_text(r.started),
             "selected": i == self._selected_result} for i, r in enumerate(results)])

        running = run is not None and run.running
        status, verdict, current = self._status(run, results)
        self._update(running=running, has_run=run is not None, verdict=verdict, status_text=status,
                     progress=len(results) / len(run.tests) if run is not None else 0.0, current_text=current,
                     elapsed_text=_minutes(self._tests.elapsed_s()) if run is not None else "",
                     checked_count=len(self._checked),
                     can_run=bool(self._checked) and not running and self._state.can("tests.run"),
                     empty_text=self._empty_message())

        shown = results[self._selected_result] if self._selected_result >= 0 else None
        self._update(output_title=f"Output · {shown.test.name}" if shown else "Output")
        self._output.set_items([{"time": "", "level": "info", "text": line} for line in shown.output] if shown else [])
        self.changed.emit()

    @staticmethod
    def _status(run: Optional[TestRun], results: List[TestResult]) -> Tuple[str, str, str]:
        """(status line, verdict, current-test line) for the run."""
        if run is None:
            return "", "", ""
        if run.running:
            done = len(results) + (1 if run.current else 0)
            current = run.stop_reason or (f"Current test: {run.current.name}" if run.current else "")
            return f"Running · test {done} of {len(run.tests)}", "running", current
        ended = "Stopped" if run.stop_reason else "Finished"
        verdict = "stopped" if run.stop_reason else ("pass" if all(r.passed for r in results) else "fail")
        return f"{ended} · {run.summary()}", verdict, run.stop_reason

    def _empty_message(self) -> str:
        """Why the test list is empty, if it is."""
        if not self._tests.loaded:
            return ""
        if self._tests.load_error:
            return f"Couldn't list the tests: {self._tests.load_error}"
        return "" if self._tests.tests else "No tests to run"
