"""Session files (~/.sirat/sessions/*.json and autosave.json, req 34) and the settings export bundle (req 2)."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sirat_ui.stores.schemas.common import NonEmpty, RegisterName, RegisterOrField, RegisterValue
from sirat_ui.stores.schemas.files import FormulaModel, clean_favorites, clean_notes
from sirat_ui.stores.schemas.operations import clean_actions
from sirat_ui.stores.schemas.report import Report, expect_dict, expect_list, validate_entry


class HistoryRecord(BaseModel):
    """HistoryLog.to_records() format. register_ is "register" in the file (see operations.RegisterField)."""
    model_config = ConfigDict(populate_by_name=True)
    ts: float = 0.0
    operation: Literal["read", "write"]
    register_: RegisterName = Field(alias="register")
    field: Optional[NonEmpty] = None
    value: RegisterValue
    register_value: Optional[RegisterValue] = None

    @field_validator("operation", mode="before")
    @classmethod
    def _lower(cls, value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value


class SessionFormula(FormulaModel):
    field: RegisterOrField


class DumpRecord(BaseModel):
    """RegisterDump.to_dict() format (req 12)."""
    name: NonEmpty
    timestamp: dt.datetime
    description: str = ""
    values: Dict[RegisterName, RegisterValue] = {}
    addresses: Dict[RegisterName, RegisterValue] = {}


class SessionHeader(BaseModel):
    model_config = ConfigDict(extra="ignore")
    session_name: NonEmpty
    created: str = ""
    modified: str = ""


def _records(model: type, items: Any, report: Report, where: str) -> List[Dict[str, Any]]:
    out = []
    for i, item in enumerate(expect_list(items, report, where)):
        record = validate_entry(model, item, report, f"{where}.{i}")
        if record is not None:
            out.append(record.model_dump(mode="json", by_alias=True))
    return out


def clean_session(raw: Any, report: Report) -> Optional[Dict[str, Any]]:
    """The session normalized, or None when it isn't a session file at all."""
    data = expect_dict(raw, report)
    header = validate_entry(SessionHeader, data, report, "")
    if header is None:
        return None

    def part(key: str, cleaner: Any) -> Any:
        sub = Report(report.source)
        result = cleaner(data.get(key), sub)
        for problem in sub.problems:
            report.add(".".join(p for p in (key, problem.where) if p), problem.message)
        return result

    return {
        **header.model_dump(mode="json"),
        "dumps": _records(DumpRecord, data.get("dumps"), report, "dumps"),
        "field_notes": part("field_notes", clean_notes),
        "formulas": _records(SessionFormula, data.get("formulas"), report, "formulas"),
        "actions": part("actions", clean_actions),
        "favorites": part("favorites", lambda raw_, r: clean_favorites(raw_ or [], r)["favorites"]),
        "history": _records(HistoryRecord, data.get("history"), report, "history"),
    }


class SettingsBundle(BaseModel):
    """The export file written by Settings > Export (domains/settings/transfer.py)."""
    model_config = ConfigDict(extra="ignore")
    format: Literal["sirat-user-settings"]
    version: int = Field(ge=1, le=1)
    app_version: str = ""
    exported: str = ""
    files: Dict[str, Any]
