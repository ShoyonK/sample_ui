"""ActionRecorder: what the pages that offer "Add to Actions" need from the Actions list, and nothing more.

ActionService implements it; add() makes the name unique (load_phy, load_phy_2, ...) and saves.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

from sirat_ui.models.actions import Action


class ActionRecorder(Protocol):
    def add(self, name: str, ops: List[Dict[str, Any]], enabled: bool = True) -> Action: ...
