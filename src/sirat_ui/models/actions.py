"""A saved action: a name, its operations and whether it's enabled (req 13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Action:
    name: str
    operations: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
