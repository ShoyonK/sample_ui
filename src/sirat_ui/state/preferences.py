"""User preferences persisted to ~/.sirat/preferences.json."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict

from sirat_ui.core.formatting import ValueFormat


@dataclass
class Preferences:
    value_format: str = ValueFormat.HEX.value
    auto_read_on_click: bool = True
    show_secure_peripherals: bool = False
    confirm_critical_writes: bool = True
    dark_mode: bool = False
    last_position: int = 1

    @property
    def format(self) -> ValueFormat:
        try:
            return ValueFormat(self.value_format)
        except ValueError:
            return ValueFormat.HEX

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: Any) -> "Preferences":
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
