"""InstrumentViewModel: what every instrument card shares, the status line and Connect for a dropped instrument.

PyQt wants a property's notify signal declared in the same class, so each card declares `changed` and builds the
shared properties with instrument_properties(changed).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSlot

from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel
from sirat_ui.state.station import StationState


def number(text: str) -> Optional[float]:
    try:
        return float(text.strip())
    except ValueError:
        return None


def _instrument_text(self: Any) -> str:
    return self._bench.describe(self.KIND)


def _found(self: Any) -> bool:
    return self._bench.instrument(self.KIND) is not None


def _connected(self: Any) -> bool:
    found = self._bench.instrument(self.KIND)
    return bool(found and found.connected)


def _errors(self: Any) -> Dict[str, str]:
    return dict(self._errors)


def _error_text(self: Any) -> str:
    return " · ".join(self._errors.values())


def instrument_properties(changed: Any) -> Tuple[pyqtProperty, ...]:
    """instrumentText, instrumentFound, instrumentConnected, errors, errorText.

    Shared by the instrument cards; a property's notify signal must belong to the class using it, hence a factory.
    """
    return (pyqtProperty(str, _instrument_text, notify=changed), pyqtProperty(bool, _found, notify=changed),
            pyqtProperty(bool, _connected, notify=changed), pyqtProperty("QVariantMap", _errors, notify=changed),
            pyqtProperty(str, _error_text, notify=changed))


class InstrumentViewModel(BaseViewModel):
    """Subclasses set KIND, declare `changed = pyqtSignal()` and the instrument_properties."""

    KIND = ""

    def __init__(self, bench: InstrumentBench, state: StationState, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._bench = bench
        self._state = state
        self._errors: Dict[str, str] = {}
        state.changed.connect(lambda *_: self.changed.emit())  # type: ignore[attr-defined]

    @pyqtSlot()
    def connectInstrument(self) -> None:  # noqa: N802
        self._bench.connect(self.KIND)

    def _set_field(self, name: str, value: str, validate: Callable[[], Dict[str, str]]) -> None:
        setattr(self, "_" + name, value)
        self._errors = validate()
        self.changed.emit()  # type: ignore[attr-defined]
