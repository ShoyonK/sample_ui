"""Register detail: header, value bar, bit grid and fields table (req §5, §7, §10, §11).

Showing and editing the register. Sending it elsewhere (favorites, watch, logger, formulas, Actions) is
shortcuts_viewmodel.py."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core import bits
from sirat_ui.core.formatting import ValueFormat, format_field, format_value, parse_value
from sirat_ui.core.observable import Event
from sirat_ui.domains.annotations.service import AnnotationService, FavoritesService
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.models.registers import FieldDef, PeripheralDef, RegisterDef
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.preferences import PreferencesState
from sirat_ui.state.selection import SelectionState
from sirat_ui.state.station import StationState

FIELD_ROLES = ["bits", "name", "fullName", "accessText", "accessKey", "valueText", "editable", "hasValue",
               "changed", "changedTip", "enumName", "enumTip", "calcText", "description", "note", "hasNote",
               "hasFormula"]


class RegisterDetailViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, state: StationState, selection: SelectionState, prefs: PreferencesState,
                 registers: RegisterService, favorites: FavoritesService, annotations: AnnotationService,
                 interactions: InteractionService, runs_finished: Event, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._selection = selection
        self._prefs = prefs
        self._registers = registers
        self._favorites = favorites
        self._annotations = annotations
        self._interactions = interactions
        self._reg: Optional[RegisterDef] = None
        self._periph: Optional[PeripheralDef] = None
        self._fields = DictListModel(FIELD_ROLES, self)
        self._mode = "empty"
        self._title = self._address_text = self._access_text = self._access_key = ""
        self._meta_text = self._description = self._value_text = self._chip_short = ""
        self._is_favorite = self._has_value = self._busy = self._show_calculated = False
        self._can_read = self._can_write = False
        self._format_index = prefs.value.format.ordinal
        self._bit_values: List[bool] = [False] * 32
        self._field_bits: List[bool] = [False] * 32
        self._register_count = 0

        selection.changed.connect(self._on_selection)
        state.changed.connect(self._refresh)
        prefs.changed.connect(lambda _: self._refresh())
        registers.value_changed.connect(self._on_value)
        favorites.changed.connect(self._refresh)
        annotations.changed.connect(self._refresh)
        runs_finished.connect(lambda ok: self._reread_quietly())   # an action may have written it

    mode = qprop(str, "_mode", changed)
    title = qprop(str, "_title", changed)
    addressText = qprop(str, "_address_text", changed)
    accessText = qprop(str, "_access_text", changed)
    accessKey = qprop(str, "_access_key", changed)
    metaText = qprop(str, "_meta_text", changed)
    description = qprop(str, "_description", changed)
    chipShort = qprop(str, "_chip_short", changed)
    isFavorite = qprop(bool, "_is_favorite", changed)
    valueText = qprop(str, "_value_text", changed)
    hasValue = qprop(bool, "_has_value", changed)
    formatIndex = qprop(int, "_format_index", changed)
    canRead = qprop(bool, "_can_read", changed)
    canWrite = qprop(bool, "_can_write", changed)
    busy = qprop(bool, "_busy", changed)
    showCalculated = qprop(bool, "_show_calculated", changed)
    bitValues = qprop("QVariantList", "_bit_values", changed)
    fieldBits = qprop("QVariantList", "_field_bits", changed)
    registerCount = qprop(int, "_register_count", changed)

    @pyqtProperty(QObject, constant=True)
    def fields(self) -> DictListModel:
        return self._fields

    @pyqtProperty(int, notify=changed)
    def fieldCount(self) -> int:  # noqa: N802
        return self._fields.count

    # ---- state -> properties ------------------------------------------------------------------

    def _on_selection(self, selection: Any, by_user: bool) -> None:
        self._reg = selection if isinstance(selection, RegisterDef) else None
        self._periph = selection if isinstance(selection, PeripheralDef) else None
        self._refresh()
        reg = self._reg
        if (by_user and reg and self._prefs.value.auto_read_on_click and reg.access.readable
                and self._state.can("registers.read")):
            self._registers.read(reg, manual=False)

    def _on_value(self, full_name: str, value: Optional[int]) -> None:
        if not full_name or (self._reg and full_name == self._reg.full_name):
            self._refresh()

    def _refresh(self) -> None:
        chip = self._state.chip
        common = dict(chip_short=chip.short if chip else "", format_index=self._prefs.value.format.ordinal)
        if self._reg:
            self._refresh_register(self._reg, common)
        elif self._periph:
            p = self._periph
            self._update(mode="peripheral", title=p.name, address_text=f"0x{p.base_address:08X}",
                         description=p.description, register_count=len(p.registers),
                         can_read=self._state.can("registers.read_many"), meta_text=f"0x{p.base_address:08X}", **common)
            self._fields.set_items([])
        else:
            self._update(mode="empty", title="", **common)
            self._fields.set_items([])

    def _refresh_register(self, reg: RegisterDef, common: Dict[str, Any]) -> None:
        value = self._registers.cached(reg.full_name)
        previous = self._registers.previous_value(reg.full_name)
        fmt = self._prefs.value.format
        field_bits = [False] * 32
        for f in reg.fields:
            for i in range(f.lsb, f.msb + 1):
                field_bits[i] = True
        self._update(
            mode="register", title=reg.full_name, address_text=f"0x{reg.address:08X}",
            access_text=reg.access.label, access_key=reg.access.value, description=reg.description,
            meta_text=f"0x{reg.address:08X} · {reg.width}-bit · reset 0x{reg.reset:08X}",
            is_favorite=self._favorites.is_favorite(reg.full_name),
            value_text=format_value(value, fmt, reg.width) if value is not None else "",
            has_value=value is not None,
            can_read=reg.access.readable and self._state.can("registers.read"),
            can_write=reg.access.writable and self._state.can("registers.write"),
            bit_values=bits.bit_list(value or 0, 32), field_bits=field_bits,
            show_calculated=any(self._annotations.formula(f.full_name) for f in reg.fields), **common,
        )
        self._fields.set_items([self._field_row(f, value, previous) for f in sorted(reg.fields, key=lambda f: -f.lsb)])
        self.changed.emit()

    def _field_row(self, f: FieldDef, value: Optional[int], previous: Optional[int]) -> Dict[str, Any]:
        raw = f.extract(value) if value is not None else None
        old = f.extract(previous) if previous is not None else None
        changed = raw is not None and old is not None and raw != old
        enum = f.enum_for(raw) if raw is not None else None
        note = self._annotations.note(f.full_name)
        return {
            "bits": f.bits_text, "name": f.name, "fullName": f.full_name,
            "accessText": f.access.label, "accessKey": f.access.value,
            "valueText": format_field(raw) if raw is not None else "—",
            "editable": f.access.writable, "hasValue": raw is not None,
            "changed": changed, "changedTip": f"Value changed: was 0x{old:X}, now 0x{raw:X}" if changed else "",
            "enumName": enum.name if enum else "", "enumTip": f"{enum.name} ({raw})\n{enum.description}" if enum else "",
            "calcText": self._annotations.format_calculated(f.full_name, raw), "description": f.description,
            "note": note, "hasNote": bool(note), "hasFormula": self._annotations.formula(f.full_name) is not None,
        }

    def _field(self, row: int) -> Optional[FieldDef]:
        name = self._fields.get(row).get("name")
        return self._reg.field(name) if self._reg and name else None

    def _reread_quietly(self) -> None:
        if self._reg and self._reg.access.readable and self._state.can("registers.read"):
            self._registers.read(self._reg, manual=False)

    # ---- user intents --------------------------------------------------------------------------

    def _run(self, call) -> None:
        self._update(busy=True)
        call.then(lambda _: self._update(busy=False), lambda _: self._update(busy=False))

    @pyqtSlot()
    def read(self) -> None:
        if self._reg:
            self._run(self._registers.read(self._reg, manual=True))

    @pyqtSlot(str)
    def write(self, text: str) -> None:
        if not self._reg:
            return
        try:
            value = parse_value(text, self._prefs.value.format)
        except ValueError as exc:
            self._interactions.toast("error", str(exc))
            return
        self._run(self._registers.write(self._reg, value))

    @pyqtSlot(int)
    def toggleBit(self, bit: int) -> None:  # noqa: N802
        if self._reg and self._can_write:
            self._run(self._registers.toggle_bit(self._reg, bit))

    @pyqtSlot(int)
    def setFormatIndex(self, index: int) -> None:  # noqa: N802
        self._prefs.update(value_format=ValueFormat.from_index(index).value)

    @pyqtSlot(int, str)
    def setFieldValue(self, row: int, text: str) -> None:  # noqa: N802
        f = self._field(row)
        if not (f and self._reg):
            return
        try:
            value = parse_value(text, ValueFormat.HEX if text.strip().lower().startswith("0x") else ValueFormat.DEC)
        except ValueError as exc:
            self._interactions.toast("error", str(exc))
            return
        self._run(self._registers.write_field(self._reg, f, value))

    @pyqtSlot(int, str)
    def setNote(self, row: int, text: str) -> None:  # noqa: N802
        f = self._field(row)
        if f:
            self._annotations.set_note(f.full_name, text)
