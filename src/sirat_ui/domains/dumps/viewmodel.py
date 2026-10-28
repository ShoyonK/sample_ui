"""Dumps page (req 12): saved dumps, Take a dump (peripheral picker + progress + name), Compare, Diff vs live,
Radio Calculator diff (req 21), and the comparison table with Save report.

The peripheral picker, progress dialog and result card are shared: pickerMode says whether the picker
starts a dump or a Radio Calculator comparison, resultKind which table the result card shows."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.dumps import Comparison
from sirat_ui.core.radio_config import STATUS_TEXT, RadioComparison, RadioConfig, parse_config, value_text
from sirat_ui.domains.dumps.service import DumpFile, DumpJob, DumpService, readable
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.sessions.service import count
from sirat_ui.shared.interactions import Alert, ConfirmRequest, InteractionService, PromptField, PromptRequest
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

CSV_FILTER = "Register dumps (*.csv)"
CFG_FILTER = "Radio Calculator config (*.cfg)"
RADIO_HELP = (
    "Each line in the .cfg is a field value Radio Calculator expects. The field's register is read from the chip "
    "and the field compared with that value.<br><br>"
    "<b>✓ Match</b>: the chip has the expected value.<br><br>"
    "<b>⚠ Mismatch</b>: the chip has a different value. Expected and Actual show both.<br><br>"
    "<b>❌ Error</b>: the field couldn't be checked. The register or field doesn't exist on this chip, the "
    "register is write-only, it's read-sensitive (reading it would clear data, so it isn't read), or the read "
    "failed. Actual says which.")
PICKER_TEXT = {
    "dump": ("Select peripherals to dump", "Every readable register of the peripherals you check is read and "
             "saved. Read-sensitive registers are skipped.", "Dump"),
    "radio": ("Select peripherals for comparison", "Each field the config sets for the peripherals you check is "
              "read from the chip and compared with the value in the config.", "Compare"),
}


def _label(f: DumpFile) -> str:
    return f"{f.name} · {f.timestamp:%Y-%m-%d %H:%M:%S}"


class DumpsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: DumpService, catalog: RegisterCatalog, state: AppState,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._catalog = catalog
        self._state = state
        self._interactions = interactions
        self._files: List[DumpFile] = []
        self._files_model = DictListModel(["name", "time", "detail", "selected"], self)
        self._peripherals = DictListModel(["name", "label", "checked"], self)
        self._rows = DictListModel(["register", "before", "after", "change"], self)
        self._radio_rows = DictListModel(["peripheral", "register", "field", "expected", "actual", "status",
                                          "statusText"], self)
        self._radio_config: Optional[RadioConfig] = None
        self._picker_mode = "dump"
        self._picker_title, self._picker_message, self._picker_confirm = PICKER_TEXT["dump"]
        self._result_kind = ""
        self._sort_column = ""
        self._sort_descending = False
        self._names: List[str] = []
        self._checked: Dict[str, bool] = {}
        self._result: Optional[Comparison] = None
        self._radio: Optional[RadioComparison] = None
        self._selected_path = ""
        self._picker_open = False
        self._checked_count = 0
        self._progress_open = False
        self._progress_title = ""
        self._progress_label = ""
        self._count_text = ""
        self._progress = 0.0
        self._cancelling = False
        self._can_read = False
        self._result_title = ""
        self._result_summary = ""
        self._before_label = "Before"
        self._after_label = "After"
        self._folder = str(service.directory)
        service.changed.connect(self.refresh)
        service.progress.connect(self._on_progress)
        state.changed.connect(self._on_state)
        self._on_state()
        self.refresh()

    files = pyqtProperty(QObject, lambda self: self._files_model, constant=True)
    peripherals = pyqtProperty(QObject, lambda self: self._peripherals, constant=True)
    rows = pyqtProperty(QObject, lambda self: self._rows, constant=True)
    radioRows = pyqtProperty(QObject, lambda self: self._radio_rows, constant=True)
    pickerMode = qprop(str, "_picker_mode", changed)
    pickerTitle = qprop(str, "_picker_title", changed)
    pickerMessage = qprop(str, "_picker_message", changed)
    pickerConfirm = qprop(str, "_picker_confirm", changed)
    resultKind = qprop(str, "_result_kind", changed)  # "" | "registers" | "radio"

    @pyqtProperty(str, notify=changed)
    def resultHelp(self) -> str:  # noqa: N802
        """The ? next to the summary: what Match, Mismatch and Error mean."""
        return RADIO_HELP if self._result_kind == "radio" else ""
    sortColumn = qprop(str, "_sort_column", changed)
    sortDescending = qprop(bool, "_sort_descending", changed)
    selectedPath = qprop(str, "_selected_path", changed)
    folder = qprop(str, "_folder", changed)
    canRead = qprop(bool, "_can_read", changed)
    pickerOpen = qprop(bool, "_picker_open", changed)
    checkedCount = qprop(int, "_checked_count", changed)
    progressOpen = qprop(bool, "_progress_open", changed)
    progressTitle = qprop(str, "_progress_title", changed)
    progressLabel = qprop(str, "_progress_label", changed)
    countText = qprop(str, "_count_text", changed)
    progress = qprop(float, "_progress", changed)
    cancelling = qprop(bool, "_cancelling", changed)
    resultTitle = qprop(str, "_result_title", changed)
    resultSummary = qprop(str, "_result_summary", changed)
    beforeLabel = qprop(str, "_before_label", changed)
    afterLabel = qprop(str, "_after_label", changed)

    @pyqtProperty(bool, notify=changed)
    def hasResult(self) -> bool:  # noqa: N802
        return self._result_kind != ""

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
        show_secure = self._state.preferences.show_secure_peripherals
        names = [p.name for p in self._catalog.peripherals
                 if (show_secure or not p.is_secure_variant) and readable(p.registers)]
        self._open_picker("dump", names, {name: self._checked.get(name, False) for name in names})

    def _open_picker(self, mode: str, names: List[str], checked: Dict[str, bool]) -> None:
        title, message, confirm = PICKER_TEXT[mode]
        self._names, self._checked = names, checked
        self._update(picker_mode=mode, picker_title=title, picker_message=message, picker_confirm=confirm,
                     picker_open=True)
        self._rebuild_peripherals()

    @pyqtSlot()
    def closePicker(self) -> None:  # noqa: N802
        self._update(picker_open=False)

    @pyqtSlot(int)
    def togglePeripheral(self, row: int) -> None:  # noqa: N802
        if 0 <= row < len(self._names):
            name = self._names[row]
            self._checked[name] = not self._checked[name]
            self._rebuild_peripherals()

    @pyqtSlot()
    def selectAll(self) -> None:  # noqa: N802
        self._checked = {name: True for name in self._names}
        self._rebuild_peripherals()

    @pyqtSlot()
    def selectNone(self) -> None:  # noqa: N802
        self._checked = {name: False for name in self._names}
        self._rebuild_peripherals()

    def _rebuild_peripherals(self) -> None:
        rows = []
        fields = self._radio_config.field_counts if self._picker_mode == "radio" and self._radio_config else {}
        for name in self._names:
            if self._picker_mode == "radio":
                label = f"{name} ({count(fields.get(name, 0), 'field')})"
            else:
                periph = self._catalog.peripheral(name)
                label = f"{name} ({count(len(readable(periph.registers)) if periph else 0, 'register')})"
            rows.append({"name": name, "label": label, "checked": self._checked[name]})
        self._peripherals.set_items(rows)
        self._update(checked_count=sum(self._checked.values()))

    @pyqtSlot()
    def startPicked(self) -> None:  # noqa: N802
        """The picker's Dump / Compare button."""
        chosen = [name for name in self._names if self._checked[name]]
        if not chosen:
            return
        if self._picker_mode == "radio" and self._radio_config is not None:
            self._update(picker_open=False, progress_title="Comparing with Radio Calculator config")
            self._service.radio_diff(self._radio_config, chosen, self._radio_done)
        else:
            self._update(picker_open=False, progress_title="Reading registers")
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

    # ---- progress dialog (shared by Take a dump and Diff vs live) -------------------------------------

    def _on_progress(self, job: DumpJob) -> None:
        if job.finished:
            self._update(progress_open=False, cancelling=False)
        else:
            verb = "Comparing" if job.kind == "radio" else "Reading"
            self._update(progress_open=True, progress_label=f"{verb} {job.current}…",
                         count_text=f"{job.index + 1} of {job.total}",
                         progress=job.index / job.total if job.total else 0.0, cancelling=job.cancelled)
        self._on_state()

    @pyqtSlot()
    def cancel(self) -> None:
        self._service.cancel()
        self._update(cancelling=True, progress_label="Cancelling after this register…")

    # ---- comparing ---------------------------------------------------------------------------------

    @pyqtSlot()
    def diffLive(self) -> None:  # noqa: N802
        chosen = self._selected()
        if chosen is None:
            return
        if not self._can_read:
            self._interactions.toast("error", "Connect to a DUT to compare with live values")
            return
        self._update(progress_title="Comparing with live values")
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
        def second(first: Optional[str]) -> None:
            if first:
                self._interactions.choose_open_file("Select the second dump", CSV_FILTER).then(
                    lambda path: path and self._compare(Path(first), Path(path)))

        self._interactions.choose_open_file("Select the first dump", CSV_FILTER).then(second)

    def _compare(self, first: Path, second: Path) -> None:
        try:
            self._show(self._service.compare_files(first, second))
        except (OSError, ValueError) as exc:
            self._interactions.alert(Alert("Couldn't compare the dumps", str(exc), "error"))

    def _comparison_done(self, result: Optional[Comparison]) -> None:
        if result is not None:  # None: cancelled or stopped
            self._show(result)

    def _radio_done(self, result: Optional[RadioComparison]) -> None:
        if result is not None:
            self._show_radio(result)

    def _show(self, result: Comparison) -> None:
        self._result, self._radio = result, None
        self._radio_rows.set_items([])
        self._rows.set_items([{"register": r.register, "before": f"0x{r.before:08X}", "after": f"0x{r.after:08X}",
                               "change": r.change} for r in result.rows])
        self._update(result_kind="registers", result_title=result.title, result_summary=result.summary,
                     before_label=result.before_label, after_label=result.after_label)

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
            self._radio_config = config
            names = list(config.field_counts)
            self._open_picker("radio", names, {name: True for name in names})

        self._interactions.choose_open_file("Select a Radio Calculator config", CFG_FILTER).then(chosen)

    def _show_radio(self, result: RadioComparison) -> None:
        self._radio, self._result = result, None
        self._rows.set_items([])
        self._update(result_kind="radio", result_title=f"Radio Calculator: {result.config_name}",
                     result_summary=result.summary, sort_column="", sort_descending=False)
        self._fill_radio_rows(result.results)

    def _fill_radio_rows(self, results) -> None:
        self._radio_rows.set_items([
            {"peripheral": r.entry.peripheral, "register": r.entry.register, "field": r.entry.field,
             "expected": value_text(r.entry.expected), "actual": r.actual_text, "status": r.status,
             "statusText": STATUS_TEXT[r.status]} for r in results])

    @pyqtSlot(str)
    def sortBy(self, column: str) -> None:  # noqa: N802
        """Click a column header to sort; click it again to reverse."""
        if self._radio is None:
            return
        descending = not self._sort_descending if column == self._sort_column else False
        self._update(sort_column=column, sort_descending=descending)
        self._fill_radio_rows(self._radio.sorted(column, descending))

    @pyqtSlot()
    def clearResult(self) -> None:  # noqa: N802
        self._result = self._radio = None
        self._rows.set_items([])
        self._radio_rows.set_items([])
        self._update(result_kind="", result_title="", result_summary="")

    @pyqtSlot()
    def saveReport(self) -> None:  # noqa: N802
        result: Optional[Union[Comparison, RadioComparison]] = self._result or self._radio
        if result is None:
            return
        title = result.title if isinstance(result, Comparison) else f"radio_{Path(result.config_name).stem}"
        suggested = str(self._service.directory / f"comparison_{title.replace(' ', '_')}.csv")

        def chosen(path: Optional[str]) -> None:
            if not path:
                return
            try:
                Path(path).write_text(result.report_csv(), encoding="utf-8-sig")  # BOM: Excel shows ✓ ⚠ ❌
                self._interactions.toast("success", f"Saved report to {path}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save the report: {exc}")

        self._interactions.choose_save_file("Save comparison report", suggested, "CSV files (*.csv)").then(chosen)
