"""Row selection with Ctrl (toggle) and Shift (range), as list widgets in the original GUI do (req 9, 18)."""

from __future__ import annotations

from typing import Hashable, List, Optional, Set


class RowSelection:
    def __init__(self) -> None:
        self.selected: Set[Hashable] = set()
        self._anchor: Optional[Hashable] = None

    def select(self, keys: List[Hashable], key: Hashable, mode: str = "single") -> None:
        """mode: "single" (plain click), "toggle" (Ctrl+click), "range" (Shift+click). keys = visible order."""
        if mode == "toggle":
            self.selected ^= {key}
            self._anchor = key
        elif mode == "range" and self._anchor in keys and key in keys:
            a, b = sorted((keys.index(self._anchor), keys.index(key)))
            self.selected = set(keys[a:b + 1])
        else:
            self.selected = {key}
            self._anchor = key

    def keep_only(self, keys) -> None:
        self.selected &= set(keys)

    def clear(self) -> None:
        self.selected.clear()
        self._anchor = None

    def __contains__(self, key: Hashable) -> bool:
        return key in self.selected
