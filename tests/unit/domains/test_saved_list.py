"""The saved-names list behind the watch list and the data logger (domains/monitoring/saved_list.py)."""

from dataclasses import dataclass

from sibench_ui.domains.monitoring.saved_list import SavedList
from sibench_ui.models.registers import RegisterDef


class StubCatalog:
    """Knows A.R1 and A.R2 once `loaded` is set; empty before that, like the catalog before connect."""

    def __init__(self) -> None:
        self.regs = {"A.R1": RegisterDef("A", "R1", 0), "A.R2": RegisterDef("A", "R2", 4)}
        self.loaded = False

    @property
    def peripherals(self):
        return ["A"] if self.loaded else []

    def resolve(self, name):
        return (self.regs.get(name) if self.loaded else None), None


@dataclass
class Item:
    name: str


def make(catalog):
    return SavedList(catalog, ["A.R1", "GONE.X", "A.R2"], lambda name, reg, fdef: Item(name))   # type: ignore[arg-type]


def test_saved_names_are_kept_until_the_catalog_loads():
    catalog = StubCatalog()
    saved = make(catalog)
    assert not saved.resolve() and saved.items == []
    assert saved.add("A.R1") is False                      # nothing resolves yet
    assert saved.names == ["A.R1", "GONE.X", "A.R2"]       # so saving keeps the file's names


def test_loading_builds_the_items_and_drops_unknown_names():
    catalog = StubCatalog()
    saved = make(catalog)
    catalog.loaded = True
    assert saved.resolve()
    assert [i.name for i in saved.items] == ["A.R1", "A.R2"]
    assert saved.add("A.R1") is False                      # already there
    saved.remove("A.R1")
    assert saved.names == ["A.R2"]


def test_a_disconnect_keeps_the_list_and_a_reconnect_rebuilds_it():
    catalog = StubCatalog()
    saved = make(catalog)
    catalog.loaded = True
    saved.resolve()
    catalog.loaded = False                                 # disconnect clears the catalog
    assert not saved.resolve() and saved.names == ["A.R1", "A.R2"]
    catalog.loaded = True
    assert saved.resolve() and [i.name for i in saved.items] == ["A.R1", "A.R2"]
