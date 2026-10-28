"""Field formula dialog (req 11): examples, Test with x = 100, Save, Remove with confirmation."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core import formula
from sirat_ui.domains.annotations.service import AnnotationService
from sirat_ui.models.dialogs import ConfirmRequest
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, qprop

TEST_X = 100
EXAMPLES = [
    {"formula": "x * 40e6 / 2**19", "unit": "Hz", "label": "Frequency from register"},
    {"formula": "(x - 32) * 5/9", "unit": "°C", "label": "Temperature F to C"},
    {"formula": "x * 3.3 / 4096", "unit": "V", "label": "Voltage from ADC"},
    {"formula": "x / 255 * 100", "unit": "%", "label": "Percentage"},
]


class FormulaEditorViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, annotations: AnnotationService, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._annotations = annotations
        self._interactions = interactions
        self._open = False
        self._field_name = ""
        self._expr = ""
        self._unit = ""
        self._test_text = ""
        self._test_ok = True
        self._has_existing = False

    isOpen = qprop(bool, "_open", changed)
    fieldName = qprop(str, "_field_name", changed)
    expr = qprop(str, "_expr", changed)
    unit = qprop(str, "_unit", changed)
    testText = qprop(str, "_test_text", changed)
    testOk = qprop(bool, "_test_ok", changed)
    hasExisting = qprop(bool, "_has_existing", changed)

    @pyqtProperty("QVariantList", constant=True)
    def examples(self):
        return EXAMPLES

    def open_for(self, field_full_name: str) -> None:
        expr, unit = self._annotations.formula(field_full_name) or ("", "")
        self._update(open=True, field_name=field_full_name, expr=expr, unit=unit, test_text="", test_ok=True,
                     has_existing=bool(expr))

    @pyqtSlot(str)
    def setExpr(self, text: str) -> None:  # noqa: N802
        self._update(expr=text, test_text="")

    @pyqtSlot(str)
    def setUnit(self, text: str) -> None:  # noqa: N802
        self._update(unit=text)

    @pyqtSlot(int)
    def useExample(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(EXAMPLES):
            self._update(expr=EXAMPLES[index]["formula"], unit=EXAMPLES[index]["unit"], test_text="")

    @pyqtSlot()
    def test(self) -> None:
        """Req 11: "User clicks Test to validate with x=100"."""
        try:
            value = formula.evaluate(self._expr, TEST_X)
            self._update(test_text=f"x = {TEST_X}  →  {formula.format_result(value, self._unit)}", test_ok=True)
        except formula.FormulaError as exc:
            self._update(test_text=str(exc), test_ok=False)

    @pyqtSlot()
    def save(self) -> None:
        if not self._expr.strip():
            self._update(test_text="Enter a formula that uses x", test_ok=False)
            return
        try:
            self._annotations.set_formula(self._field_name, self._expr, self._unit)
        except ValueError as exc:
            self._update(test_text=str(exc), test_ok=False)
            return
        self._interactions.toast("success", f"Saved formula for {self._field_name}")
        self.cancel()

    @pyqtSlot()
    def remove(self) -> None:
        name = self._field_name
        request = ConfirmRequest("Remove formula", f"Are you sure? The calculated value for {name} will go away.",
                                 confirm_text="Remove", tone="danger")

        def answered(answer) -> None:
            if answer.accepted:
                self._annotations.set_formula(name, "", "")
                self._interactions.toast("info", f"Removed formula for {name}")
                self.cancel()

        self._interactions.confirm(request).then(answered)

    @pyqtSlot()
    def cancel(self) -> None:
        self._update(open=False)
