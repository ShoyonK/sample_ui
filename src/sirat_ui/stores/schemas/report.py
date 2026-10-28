"""Collecting validation problems, and the two ways files are validated.

Settings files are shared with the old SiRAT GUI, edited by hand and copied between stations, so one bad
entry must not throw away the rest. Collections (actions, sequences, favorites...) are validated entry by
entry: valid entries are kept, invalid ones are skipped and reported. Records with defaults (preferences,
hardware config) keep every valid field and fall back to the default for invalid ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)


@dataclass(frozen=True)
class Problem:
    source: str   # file name, e.g. ".sirat_actions.json"
    where: str    # path inside it, e.g. "lpmode_on.operations.0.value"
    message: str

    def __str__(self) -> str:
        return f"{self.source}: {self.where}: {self.message}" if self.where else f"{self.source}: {self.message}"


@dataclass
class Report:
    source: str
    problems: List[Problem] = field(default_factory=list)

    def add(self, where: str, message: str) -> None:
        self.problems.append(Problem(self.source, where, message))

    def add_error(self, where: str, error: ValidationError) -> None:
        for item in error.errors():
            loc = ".".join(str(part) for part in item["loc"])
            self.add(".".join(p for p in (where, loc) if p), _message(item["msg"]))

    def __bool__(self) -> bool:
        return bool(self.problems)


def _message(msg: str) -> str:
    return msg[len("Value error, "):] if msg.startswith("Value error, ") else msg


def validate_entry(model: Type[M], value: Any, report: Report, where: str) -> Optional[M]:
    """The validated entry, or None (and a reported problem) when it's invalid."""
    try:
        return model.model_validate(value)
    except ValidationError as error:
        report.add_error(where, error)
        return None


def validate_with_defaults(model: Type[M], raw: Any, report: Report) -> M:
    """Keeps every valid field; an invalid field is reported and gets the model's default."""
    data: Dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    if not isinstance(raw, dict) and raw is not None:
        report.add("", f"expected an object, got {type(raw).__name__}; using defaults")
    for _ in range(len(data) + 1):
        try:
            return model.model_validate(data)
        except ValidationError as error:
            bad = {str(item["loc"][0]) for item in error.errors() if item["loc"]}
            report.add_error("", error)
            if not bad:
                break
            for key in bad:
                data.pop(key, None)
    return model()


def expect_dict(raw: Any, report: Report) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw is not None:
        report.add("", f"expected an object, got {type(raw).__name__}; ignoring the file's contents")
    return {}


def expect_list(raw: Any, report: Report, where: str = "") -> List[Any]:
    if isinstance(raw, list):
        return raw
    if raw is not None:
        report.add(where, f"expected a list, got {type(raw).__name__}")
    return []
