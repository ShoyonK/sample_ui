"""Dumps page (req 12): saved dumps, and starting each kind of comparison.

Take a dump, Diff vs live, Compare with, Compare files and Radio Calculator diff (req 21) start here; the
peripheral picker (picker_viewmodel.py), the progress dialog (progress_viewmodel.py) and the comparison card
(comparison_viewmodel.py) are separate ViewModels this one drives.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.radio_config import parse_config, RadioComparison
from sirat_ui.domains.dumps.comparison_viewmodel import ComparisonViewModel
from sirat_ui.domains.dumps.picker_viewmodel import PeripheralPickerViewModel
from sirat_ui.domains.dumps.progress_viewmodel import DumpProgressViewModel
from sirat_ui.domains.dumps.service import DumpFile, DumpJob, DumpService, readable
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.sessions.service import count
from sirat_ui.models.dialogs import Alert, ConfirmRequest, PromptField, PromptRequest
from sirat_ui.models.dumps import Comparison
from sirat_ui.models.radio import RadioConfig
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.preferences import PreferencesState
from sirat_ui.state.station import StationState

CSV_FILTER = "Register dumps (*.csv)"
CFG_FILTER = "Radio Calculator config (*.cfg)"
DUMP_WORDING = ("Select peripherals to dump", "Every readable register of the peripherals you check is read and "
                "saved. Read-sensitive registers are skipped.", "Dump")
RADIO_WORDING = ("Select peripherals for comparison", "Each field the config sets for the peripherals you check is "
                 "read from the chip and compared with the value in the config.", "Compare")


def _label(f: DumpFile) -> str:
    return f"{f.name} · {f.timestamp:%Y-%m-%d %H:%M:%S}"


class DumpsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: DumpService, catalog: RegisterCatalog, state: StationState, prefs: PreferencesState,
                 interactions: InteractionService, picker: PeripheralPickerViewModel,
                 progress: DumpProgressViewModel, comparison: ComparisonViewModel, samples_dir: Path,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._samples_dir = samples_dir
        self._catalog = catalog
        self._state = state
        self._prefs = prefs
        self._interactions = interactions
        self._picker = picker
        self._progress = progress
        self._comparison = comparison
        self._files: List[DumpFile] = []
        self._files_model = DictListModel(["name", "time", "detail", "selected"], self)
        self._dump_checked: Dict[str, bool] = {}   # the picker remembers what you dumped last time
        self._selected_path = ""
        self._can_read = False
        self._folder = str(service.directory)
        service.changed.connect(self.refresh)
        service.progress.connect(lambda _: self._on_state())
        state.changed.connect(self._on_state)
        self._on_state()
        self.refresh()

    @pyqtProperty(QObject, constant=True)
    def files(self) -> QObject:
        return self._files_model

    selectedPath = qprop(str, "_selected_path", changed)
    folder = qprop(str, "_folder", changed)
    canRead = qprop(bool, "_can_read", changed)

    def _on_state(self, *_) -> None:
        self._update(can_read=self._state.facts.dut_connected and not self._service.running)

    # ---- saved dumps ------------------------------------------------------------------------------

    @pyqtSlot()
    def refresh(self) -> None:
        self._files = self._service.files()
        if self._selected_path and not any(str(f.path) == self._selected_path for f in self._files):
            self._update(selected_path="")
        self._files_model.set_items([
            {"name": f.name, "time": f"{f.timestamp:%Y-%m-%d %H:%M:%S}",
             "detail": f"{count(f.registers, 'register')} · {', '.join(f.peripherals[:4])}"
                       + (" …" if len(f.peripherals) > 4 else ""),
             "selected": str(f.path) == self._selected_path}
            for f in self._files])

    @pyqtSlot(int)
    def select(self, row: int) -> None:
        if 0 <= row < len(self._files):
            self._update(selected_path=str(self._files[row].path))
            self.refresh()

    def _selected(self) -> Optional[DumpFile]:
        return next((f for f in self._files if str(f.path) == self._selected_path), None)

    @pyqtSlot()
    def deleteSelected(self) -> None:  # noqa: N802
        chosen = self._selected()
        if chosen is None:
            return
        request = ConfirmRequest(f"Delete dump {chosen.name}?", f"{chosen.path.name} is removed. You can't undo it.",
                                 confirm_text="Delete", tone="danger")
        self._interactions.confirm(request).then(
            lambda a: self._service.delete(chosen.path) if a.accepted else None)

    # ---- Take a dump --------------------------------------------------------------------------------

    @pyqtSlot()
    def openPicker(self) -> None:  # noqa: N802
        if not self._can_read:
            self._interactions.toast("error", "Connect to a DUT to take a dump")
            return
        show_secure = self._prefs.value.show_secure_peripherals
        names = [p.name for p in self._catalog.peripherals
                 if (show_secure or not p.is_secure_variant) and readable(p.registers)]

        def label(name: str) -> str:
            periph = self._catalog.peripheral(name)
            return f"{name} ({count(len(readable(periph.registers)) if periph else 0, 'register')})"

        self._picker.open("dump", DUMP_WORDING, {n: self._dump_checked.get(n, False) for n in names}, label,
                          self._take)

    def _take(self, chosen: List[str]) -> None:
        self._dump_checked = self._picker.checked()
        self._progress.begin("Reading registers")
        self._service.take(chosen, self._dump_read)

    def _dump_read(self, job: DumpJob) -> None:
        if job.cancelled:
            self._interactions.toast("info", "Dump cancelled")
            return
        if job.stopped_reason:
            self._interactions.alert(Alert("Dump stopped", f"The dump stopped: {job.stopped_reason}. Nothing was saved.",
                                           "error"))
            return
        message = f"Read {count(len(job.values), 'register')}"
        if job.failed:
            message += f"; {job.failed} couldn't be read and are left out"
        fields = [PromptField("name", "Dump name", "dump"),
                  PromptField("description", "Description", placeholder="Optional, kept in saved sessions")]

        def named(values) -> None:
            name = (values or {}).get("name", "").strip()
            if not name:
                self._interactions.toast("info", "Dump discarded")
                return
            dump = self._service.new_dump(job, name, (values or {}).get("description", "").strip())
            try:
                path = self._service.save(dump)
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save the dump: {exc}")
                return
            self._update(selected_path=str(path))
            self.refresh()
            self._interactions.toast("success", "Finished taking a dump \U0001F4A9")

        self._interactions.prompt(PromptRequest("Name this dump", fields, message=message + ".",
                                                confirm_text="Save")).then(named)

    # ---- comparing ---------------------------------------------------------------------------------

    @pyqtSlot()
    def diffLive(self) -> None:  # noqa: N802
        chosen = self._selected()
        if chosen is None:
            return
        if not self._can_read:
            self._interactions.toast("error", "Connect to a DUT to compare with live values")
            return
        self._progress.begin("Comparing with live values")
        try:
            self._service.diff_live(chosen.path, self._comparison_done)
        except (OSError, ValueError) as exc:
            self._interactions.alert(Alert("Couldn't read the dump", str(exc), "error"))

    @pyqtSlot()
    def compareWith(self) -> None:  # noqa: N802
        """Compares the selected dump with another saved one, picked from a drop-down."""
        chosen = self._selected()
        others = [f for f in self._files if f is not chosen]
        if chosen is None:
            return
        if not others:
            self._interactions.toast("info", "Take another dump to compare with")
            return
        labels = {_label(f): f for f in others}
        field = PromptField("other", "Compare with", next(iter(labels)), options=list(labels))

        def answered(values) -> None:
            other = labels.get((values or {}).get("other", ""))
            if other is not None:
                self._compare(chosen.path, other.path)

        self._interactions.prompt(PromptRequest(f"Compare {chosen.name}", [field],
                                                message="The older dump is shown as Before.",
                                                confirm_text="Compare")).then(answered)

    @pyqtSlot()
    def compareFiles(self) -> None:  # noqa: N802
        """Req 12 Compare Dumps: two file dialogs, then the comparison."""
        folder = self._service.directory

        def second(first: Optional[str]) -> None:
            if first:
                self._interactions.choose_open_file("Select the second dump", CSV_FILTER, folder).then(
                    lambda path: path and self._compare(Path(first), Path(path)))

        self._interactions.choose_open_file("Select the first dump", CSV_FILTER, folder).then(second)

    def _compare(self, first: Path, second: Path) -> None:
        try:
            self._comparison.show(self._service.compare_files(first, second))
        except (OSError, ValueError) as exc:
            self._interactions.alert(Alert("Couldn't compare the dumps", str(exc), "error"))

    def _comparison_done(self, result: Optional[Comparison]) -> None:
        if result is not None:
            self._comparison.show(result)
        else:
            self._explain_stop()

    # ---- Radio Calculator diff (req 21) ------------------------------------------------------------

    @pyqtSlot()
    def openRadioDiff(self) -> None:  # noqa: N802
        """Pick a .cfg, then the peripherals to compare (all checked to start with)."""
        if not self._can_read:
            self._interactions.toast("error", "Connect to a DUT to compare with a Radio Calculator config")
            return

        def chosen(path: Optional[str]) -> None:
            if not path:
                return
            try:
                config = parse_config(Path(path).read_text(encoding="utf-8-sig"), Path(path).name)
            except (OSError, UnicodeDecodeError) as exc:
                self._interactions.alert(Alert("Couldn't read the config", str(exc), "error"))
                return
            if not config.entries:
                self._interactions.alert(Alert("No fields in the config", f"{config.name} has no lines like "
                                               "PERIPHERAL.REGISTER.FIELD = value.", "warning"))
                return
            if config.skipped:
                self._interactions.toast("warning", f"Skipped {count(len(config.skipped), 'line')} in {config.name} "
                                                    f"that aren't PERIPHERAL.REGISTER.FIELD = value")
            self._open_radio_picker(config)

        self._interactions.choose_open_file("Select a Radio Calculator config", CFG_FILTER, self._samples_dir).then(chosen)

    def _open_radio_picker(self, config: RadioConfig) -> None:
        fields = config.field_counts

        def start(names: List[str]) -> None:
            self._progress.begin("Comparing with Radio Calculator config")
            self._service.radio_diff(config, names, self._radio_done)

        self._picker.open("radio", RADIO_WORDING, {name: True for name in fields},
                          lambda name: f"{name} ({count(fields.get(name, 0), 'field')})", start)

    def _radio_done(self, result: Optional[RadioComparison]) -> None:
        if result is not None:
            self._comparison.show_radio(result)
        else:
            self._explain_stop()

    def _explain_stop(self) -> None:
        """A comparison came back empty: cancelled, or stopped part way (the DUT went away, say)."""
        job = self._service.job
        if job is not None and job.stopped_reason:
            self._interactions.alert(Alert("Comparison stopped", f"The comparison stopped: {job.stopped_reason}.", "error"))
        else:
            self._interactions.toast("info", "Comparison cancelled")
