"""Ctrl+K command palette (frontend plan, section 4.4): jump to registers, pages, actions, sequences, commands.

Ranking: exact match, then prefix, then a word starting with the query, then anywhere; shorter first.
Registers also match on field names ("opmode" finds MODEM.CTRL).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.automation.sequences import SequenceService
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.shell.viewmodels import PAGES
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

MAX_RESULTS = 30
KIND_ORDER = {"command": 0, "page": 1, "register": 2, "action": 3, "sequence": 4}


@dataclass
class Command:
    key: str
    title: str
    subtitle: str
    run: Callable[[], object]  # return value ignored


@dataclass
class Entry:
    kind: str
    key: str
    title: str
    subtitle: str
    search: str  # lower-case text matched against the query
    rank: int = 9


def _rank(query: str, text: str) -> Optional[int]:
    if text == query:
        return 0
    if text.startswith(query):
        return 1
    if any(word.startswith(query) for word in text.replace(".", " ").replace("_", " ").split()):
        return 2
    if query in text:
        return 3
    return None


class CommandPaletteViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, state: AppState, catalog: RegisterCatalog, actions: ActionService,
                 sequences: SequenceService, navigate: Callable[[str], None],
                 select_action: Callable[[str], None], select_sequence: Callable[[str], None],
                 commands: List[Command], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._catalog = catalog
        self._actions = actions
        self._sequences = sequences
        self._navigate = navigate
        self._select_action = select_action
        self._select_sequence = select_sequence
        self._commands: Dict[str, Command] = {c.key: c for c in commands}
        self._model = DictListModel(["kind", "key", "title", "subtitle", "current"], self)
        self._open = False
        self._query = ""
        self._current = 0

    isOpen = qprop(bool, "_open", changed)
    query = qprop(str, "_query", changed)
    currentIndex = qprop(int, "_current", changed)

    @pyqtProperty(QObject, constant=True)
    def results(self) -> DictListModel:
        return self._model

    # ---- entries ---------------------------------------------------------------------------------

    def _entries(self) -> List[Entry]:
        entries = [Entry("command", c.key, c.title, c.subtitle, c.title.lower()) for c in self._commands.values()]
        entries += [Entry("page", p["key"], p["title"], "Page" + ("" if p["ready"] else " · planned"),
                          p["title"].lower()) for p in PAGES]
        for periph in self._catalog.search("").peripherals:
            p = self._catalog.peripheral(periph)
            for reg in p.registers if p else ():
                fields = " ".join(f.name.lower() for f in reg.fields)
                entries.append(Entry("register", reg.full_name, reg.full_name,
                                     f"0x{reg.address:08X} · {reg.description}", f"{reg.full_name.lower()} {fields}"))
        entries += [Entry("action", name, name, "Action", name.lower()) for name in self._actions.actions]
        entries += [Entry("sequence", name, name, "Sequence", name.lower()) for name in self._sequences.sequences]
        return entries

    def _search(self) -> List[Entry]:
        query = self._query.strip().lower()
        entries = self._entries()
        if not query:
            return [e for e in entries if e.kind in ("command", "page")][:MAX_RESULTS]
        hits = []
        for e in entries:
            title_rank = _rank(query, e.title.lower())
            if e.kind == "register":  # "lpmode" should find BUFC.LPMODE as readily as "bufc" does
                short_rank = _rank(query, e.title.lower().split(".", 1)[-1])
                if short_rank is not None and (title_rank is None or short_rank < title_rank):
                    title_rank = short_rank
            rank = title_rank if title_rank is not None else (4 if query in e.search else None)
            if rank is not None:
                e.rank = rank
                if title_rank is None and e.kind == "register":
                    reg = self._catalog.register(e.key)
                    field = next((f.name for f in reg.fields if query in f.name.lower()), "") if reg else ""
                    e.subtitle = f"field {field} · {e.subtitle}"
                hits.append(e)
        hits.sort(key=lambda e: (e.rank, KIND_ORDER[e.kind], len(e.title), e.title))
        return hits[:MAX_RESULTS]

    def _rebuild(self) -> None:
        hits = self._search()
        self._current = max(0, min(self._current, len(hits) - 1))
        self._model.set_items([{"kind": e.kind, "key": e.key, "title": e.title, "subtitle": e.subtitle,
                                "current": i == self._current} for i, e in enumerate(hits)])
        self.changed.emit()

    # ---- user intents ------------------------------------------------------------------------------

    @pyqtSlot()
    def open(self) -> None:
        self._update(open=True, query="", current=0)
        self._rebuild()

    @pyqtSlot()
    def close(self) -> None:
        self._update(open=False)

    @pyqtSlot(str)
    def setQuery(self, text: str) -> None:  # noqa: N802
        self._update(query=text, current=0)
        self._rebuild()

    @pyqtSlot(int)
    def move(self, delta: int) -> None:
        if self._model.count:
            self._current = (self._current + delta) % self._model.count
            self._rebuild()

    @pyqtSlot()
    def activateCurrent(self) -> None:  # noqa: N802
        self.activate(self._current)

    @pyqtSlot(int)
    def activate(self, row: int) -> None:
        item = self._model.get(row)
        if not item:
            return
        self.close()
        kind, key = item["kind"], item["key"]
        if kind == "command":
            self._commands[key].run()
        elif kind == "page":
            self._navigate(key)
        elif kind == "register":
            self._navigate("registers")
            reg = self._catalog.register(key)
            if reg:
                self._state.select(reg, by_user=True)  # opens it and auto-reads, like a tree click
        elif kind == "action":
            self._navigate("actions")
            self._select_action(key)
        elif kind == "sequence":
            self._navigate("sequences")
            self._select_sequence(key)
