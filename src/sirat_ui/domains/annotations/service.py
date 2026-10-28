"""Favorites (req §8), field notes (req §10) and field formulas (req §11). GUI-only, persisted."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sirat_ui.core import formula
from sirat_ui.core.observable import Event
from sirat_ui.stores.formats import read_favorites, read_formulas, write_favorites, write_formulas
from sirat_ui.stores.json_store import JsonStore


class FavoritesService:
    def __init__(self, store: JsonStore) -> None:
        self._store = store
        self.names: List[str] = read_favorites(store.load())
        self.changed = Event()

    def reload(self) -> None:
        self.names = read_favorites(self._store.load())
        self.changed.emit()

    def replace(self, names: List[str]) -> None:
        self.names = list(dict.fromkeys(names))
        self._save()

    def is_favorite(self, full_name: str) -> bool:
        return full_name in self.names

    def toggle(self, full_name: str) -> bool:
        if full_name in self.names:
            self.names.remove(full_name)
        else:
            self.names.append(full_name)
        self._save()
        return full_name in self.names

    def remove(self, full_name: str) -> None:
        if full_name in self.names:
            self.names.remove(full_name)
            self._save()

    def _save(self) -> None:
        self._store.save(write_favorites(self.names))
        self.changed.emit()


class AnnotationService:
    def __init__(self, notes_store: JsonStore, formulas_store: JsonStore) -> None:
        self._notes_store = notes_store
        self._formulas_store = formulas_store
        notes = notes_store.load()
        self.notes: Dict[str, str] = dict(notes) if isinstance(notes, dict) else {}
        self.formulas: Dict[str, Tuple[str, str]] = read_formulas(formulas_store.load())
        self.changed = Event()

    def reload(self) -> None:
        notes = self._notes_store.load()
        self.notes = dict(notes) if isinstance(notes, dict) else {}
        self.formulas = read_formulas(self._formulas_store.load())
        self.changed.emit()

    def replace(self, notes: Dict[str, str], formulas: Dict[str, Tuple[str, str]]) -> None:
        self.notes = {k: v for k, v in notes.items() if v}
        self.formulas = dict(formulas)
        self._notes_store.save(self.notes)
        self._formulas_store.save(write_formulas(self.formulas))
        self.changed.emit()

    # ---- notes ------------------------------------------------------------

    def note(self, full_name: str) -> str:
        return self.notes.get(full_name, "")

    def set_note(self, full_name: str, text: str) -> None:
        text = (text or "").strip()
        if text == self.notes.get(full_name, ""):
            return
        if text:
            self.notes[full_name] = text
        else:
            self.notes.pop(full_name, None)
        self._notes_store.save(self.notes)
        self.changed.emit()

    # ---- formulas ---------------------------------------------------------

    def formula(self, full_name: str) -> Optional[Tuple[str, str]]:
        return self.formulas.get(full_name)

    def set_formula(self, full_name: str, expr: str, unit: str = "") -> None:
        """Empty expr removes the formula. Raises ValueError for an invalid formula."""
        if not (expr or "").strip():
            self.formulas.pop(full_name, None)
        else:
            error = formula.validate(expr)
            if error:
                raise ValueError(error)
            self.formulas[full_name] = (expr.strip(), (unit or "").strip())
        self._formulas_store.save(write_formulas(self.formulas))
        self.changed.emit()

    def calculate(self, full_name: str, raw: int) -> Optional[float]:
        entry = self.formulas.get(full_name)
        if not entry:
            return None
        try:
            return formula.evaluate(entry[0], raw)
        except formula.FormulaError:
            return None

    def format_calculated(self, full_name: str, raw: Optional[int]) -> str:
        entry = self.formulas.get(full_name)
        if not entry or raw is None:
            return ""
        value = self.calculate(full_name, raw)
        return "error" if value is None else formula.format_result(value, entry[1])
