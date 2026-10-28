"""StatusLine: the one-line message at the bottom of the window ("CMU.CTRL @ 0x40008004 · read ok")."""

from __future__ import annotations

from sirat_ui.core.observable import Event


class StatusLine:
    def __init__(self, text: str = "Ready") -> None:
        self.text = text
        self.changed = Event()

    def set(self, text: str) -> None:
        self.text = text
        self.changed.emit()
