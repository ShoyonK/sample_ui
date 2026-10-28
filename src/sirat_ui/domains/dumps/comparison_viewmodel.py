"""The comparison card on the Dumps page: a register comparison (req 12) or a Radio Calculator diff (req 21),
with sorting for the radio table and Save report."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.radio_config import RadioComparison, STATUS_TEXT, value_text
from sirat_ui.models.dumps import Comparison
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop

RADIO_HELP = (
    "Each line in the .cfg is a field value Radio Calculator expects. The field's register is read from the chip "
    "and the field compared with that value.<br><br>"
    "<b>✓ Match</b>: the chip has the expected value.<br><br>"
    "<b>⚠ Mismatch</b>: the chip has a different value. Expected and Actual show both.<br><br>"
    "<b>❌ Error</b>: the field couldn't be checked. The register or field doesn't exist on this chip, the "
    "register is write-only, it's read-sensitive (reading it would clear data, so it isn't read), or the read "
    "failed. Actual says which.")


class ComparisonViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, reports_dir: Path, interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._reports_dir = reports_dir
        self._interactions = interactions
        self._rows = DictListModel(["register", "before", "after", "change"], self)
        self._radio_rows = DictListModel(["peripheral", "register", "field", "expected", "actual", "status",
                                          "statusText"], self)
        self._result: Optional[Comparison] = None
        self._radio: Optional[RadioComparison] = None
        self._result_kind = ""
        self._result_title = self._result_summary = ""
        self._sort_column = ""
        self._sort_descending = False
        self._match_count = self._mismatch_count = self._error_count = 0
        self._before_label, self._after_label = "Before", "After"

    @pyqtProperty(QObject, constant=True)
    def rows(self) -> QObject:
        return self._rows

    @pyqtProperty(QObject, constant=True)
    def radioRows(self) -> QObject:  # noqa: N802
        return self._radio_rows

    resultKind = qprop(str, "_result_kind", changed)  # "" | "registers" | "radio"
    resultTitle = qprop(str, "_result_title", changed)
    resultSummary = qprop(str, "_result_summary", changed)
    sortColumn = qprop(str, "_sort_column", changed)
    sortDescending = qprop(bool, "_sort_descending", changed)
    matchCount = qprop(int, "_match_count", changed)
    mismatchCount = qprop(int, "_mismatch_count", changed)
    errorCount = qprop(int, "_error_count", changed)
    beforeLabel = qprop(str, "_before_label", changed)
    afterLabel = qprop(str, "_after_label", changed)

    @pyqtProperty(bool, notify=changed)
    def hasResult(self) -> bool:  # noqa: N802
        return self._result_kind != ""

    @pyqtProperty(str, notify=changed)
    def resultHelp(self) -> str:  # noqa: N802
        """The ? next to the summary: what Match, Mismatch and Error mean."""
        return RADIO_HELP if self._result_kind == "radio" else ""

    def show(self, result: Comparison) -> None:
        self._result, self._radio = result, None
        self._radio_rows.set_items([])
        self._rows.set_items([{"register": r.register, "before": f"0x{r.before:08X}", "after": f"0x{r.after:08X}",
                               "change": r.change} for r in result.rows])
        self._update(result_kind="registers", result_title=result.title, result_summary=result.summary,
                     before_label=result.before_label, after_label=result.after_label)

    def show_radio(self, result: RadioComparison) -> None:
        self._radio, self._result = result, None
        self._rows.set_items([])
        self._update(result_kind="radio", result_title=f"Radio Calculator: {result.config_name}",
                     result_summary=result.summary, sort_column="", sort_descending=False,
                     match_count=result.counts["match"], mismatch_count=result.counts["mismatch"],
                     error_count=result.counts["error"])
        self._fill_radio_rows(result.results)

    def _fill_radio_rows(self, results) -> None:
        self._radio_rows.set_items([
            {"peripheral": r.entry.peripheral, "register": r.entry.register, "field": r.entry.field,
             "expected": value_text(r.entry.expected), "actual": r.actual_text, "status": r.status,
             "statusText": STATUS_TEXT[r.status].split(" ", 1)[1]} for r in results])  # the icon shows the mark

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
        suggested = str(self._reports_dir / f"comparison_{title.replace(' ', '_')}.csv")

        def chosen(path: Optional[str]) -> None:
            if not path:
                return
            try:
                Path(path).write_text(result.report_csv(), encoding="utf-8-sig")  # BOM: Excel shows ✓ ⚠ ❌
                self._interactions.toast("success", f"Saved report to {path}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't save the report: {exc}")

        self._interactions.choose_save_file("Save comparison report", suggested, "CSV files (*.csv)").then(chosen)
