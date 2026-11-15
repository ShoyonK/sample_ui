"""A list of registers or fields saved by name, shared by the watch list (req 18) and the data logger (req 17).

The names are saved to a file, but an item needs the register's definition, which only exists once the register
catalog loads. So the list keeps the saved names until then, builds its items when the catalog loads, and keeps
the items' names on a disconnect (when the catalog is cleared) so nothing the user added is lost.
"""

from __future__ import annotations

from typing import Callable, Generic, List, Optional, Protocol, TypeVar

from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.models.registers import FieldDef, RegisterDef


class Named(Protocol):
    name: str


T = TypeVar("T", bound=Named)


class SavedList(Generic[T]):
    """The items of one list, built from saved names once the catalog can resolve them.

    Args:
        catalog: Resolves "PERIPHERAL.REGISTER[.FIELD]" names.
        names: The names read from the file.
        make: Builds an item from its name and resolved register (and field, for a field).
    """

    def __init__(self, catalog: RegisterCatalog, names: List[str],
                 make: Callable[[str, RegisterDef, Optional[FieldDef]], T]) -> None:
        self._catalog = catalog
        self._make = make
        self.items: List[T] = []
        self._saved = list(names)
        self._resolved = False

    def reset(self, names: List[str]) -> None:
        """Starts over from names read from the file again; the items are rebuilt by resolve()."""
        self._saved = list(names)
        self.items = []
        self._resolved = False

    @property
    def names(self) -> List[str]:
        """The names to save: the items' names, or the saved names while the catalog hasn't loaded yet."""
        return [i.name for i in self.items] if self._resolved else list(self._saved)

    def resolve(self) -> bool:
        """Rebuilds the items against the catalog. Returns False (and changes nothing) while it's empty."""
        if not self._catalog.peripherals:
            return False   # catalog cleared on disconnect: keep the list as it is
        names = self.names
        self._resolved = True
        self.items = []
        for name in names:
            self.add(name)
        return True

    def add(self, full_name: str) -> bool:
        """Adds an item. Returns False when it's already in the list or the catalog doesn't know the name."""
        if any(i.name == full_name for i in self.items):
            return False
        reg, fdef = self._catalog.resolve(full_name)
        if reg is None:
            return False
        self.items.append(self._make(full_name, reg, fdef))
        return True

    def remove(self, full_name: str) -> None:
        self.items = [i for i in self.items if i.name != full_name]

    def clear(self) -> None:
        self.items = []

    def get(self, full_name: str) -> Optional[T]:
        return next((i for i in self.items if i.name == full_name), None)
