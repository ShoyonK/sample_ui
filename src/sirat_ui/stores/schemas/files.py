"""Schemas for the other settings files (req 1 auto-loaded files; formats in sirat_requirements.txt).

Each clean_* takes the file's raw JSON and returns it validated and normalized to the original format (legacy
forms earlier builds wrote are converted), with every skipped entry reported.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated

from sirat_ui.core.formula import validate as formula_problem
from sirat_ui.stores.schemas.common import NonEmpty, RegisterName, RegisterOrField
from sirat_ui.stores.schemas.report import (Report, expect_dict, expect_list, validate_entry,
                                            validate_with_defaults)


class _Name(BaseModel):
    """Wraps one list item so it can be validated (and reported) on its own."""
    value: RegisterOrField


class _RegisterItem(BaseModel):
    value: RegisterName


def _names(items: Any, report: Report, where: str, model: type = _Name) -> List[str]:
    out = []
    for i, item in enumerate(expect_list(items, report, where)):
        checked = validate_entry(model, {"value": item}, report, f"{where}.{i}")
        if checked is not None:
            out.append(checked.value)
    return out


def _rate(value: Any, default: float, report: Report, where: str) -> float:
    class _Rate(BaseModel):
        value: float = Field(gt=0, le=3600)

    if value is None:
        return default
    checked = validate_entry(_Rate, {"value": value}, report, where)
    return checked.value if checked else default


# ---- ~/.sirat_favorites.json (req 8) -----------------------------------------------------------------

def clean_favorites(raw: Any, report: Report) -> Dict[str, Any]:
    items = raw.get("favorites") if isinstance(raw, dict) else raw  # earlier builds wrote a plain list
    return {"favorites": _names(items, report, "favorites", _RegisterItem)}


# ---- ~/.sirat_watch_list.json (req 18) and ~/.sirat_data_logger.json (req 17) ----------------------------

def clean_watch_list(raw: Any, report: Report) -> Dict[str, Any]:
    if isinstance(raw, list):  # earlier builds
        raw = {"watched_fields": raw}
    data = expect_dict(raw, report)
    return {"watched_fields": _names(data.get("watched_fields"), report, "watched_fields"),
            "refresh_rate": _rate(data.get("refresh_rate"), 1.0, report, "refresh_rate")}


def clean_data_logger(raw: Any, report: Report) -> Dict[str, Any]:
    data = expect_dict(raw, report)
    names = data.get("tracked_fields", data.get("fields"))  # "fields"/"rate_s": earlier builds
    rate = data.get("sample_rate", data.get("rate_s"))
    return {"tracked_fields": _names(names, report, "tracked_fields"),
            "sample_rate": _rate(rate, 1.0, report, "sample_rate")}


# ---- ~/.sirat_sequences.json (req 14) ---------------------------------------------------------------------

class SequenceModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    action_names: List[NonEmpty] = []
    description: str = ""

    @model_validator(mode="before")
    @classmethod
    def _legacy_list(cls, value: Any) -> Any:
        return {"action_names": value} if isinstance(value, list) else value


def clean_sequences(raw: Any, report: Report) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, value in expect_dict(raw, report).items():
        sequence = validate_entry(SequenceModel, value, report, name)
        if sequence is not None:
            out[name] = sequence.model_dump(mode="json")
    return out


# ---- ~/.sirat/field_formulas.json (req 11) and field_notes.json (req 10) -------------------------------------

class FormulaModel(BaseModel):
    formula: NonEmpty
    unit: str = ""

    @model_validator(mode="before")
    @classmethod
    def _legacy_pair(cls, value: Any) -> Any:  # earlier builds wrote [formula, unit]
        if isinstance(value, (list, tuple)) and value:
            return {"formula": value[0], "unit": value[1] if len(value) > 1 else ""}
        return value

    @field_validator("formula")
    @classmethod
    def _parses(cls, value: str) -> str:
        problem = formula_problem(value)
        if problem:
            raise ValueError(problem)
        return value


class _FieldKey(BaseModel):
    value: RegisterOrField


def clean_formulas(raw: Any, report: Report) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, value in expect_dict(raw, report).items():
        key = validate_entry(_FieldKey, {"value": name}, report, name)
        formula = validate_entry(FormulaModel, value, report, name)
        if key is not None and formula is not None:
            out[key.value] = formula.model_dump(mode="json")
    return out


class _Note(BaseModel):
    field: RegisterOrField
    note: str


def clean_notes(raw: Any, report: Report) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, value in expect_dict(raw, report).items():
        note = validate_entry(_Note, {"field": name, "note": value}, report, name)
        if note is not None:
            out[note.field] = note.note
    return out


# ---- ~/.sirat_custom_functions.json (req 15) ------------------------------------------------------------------

class CustomFunctionModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: NonEmpty
    code: str = ""


def clean_custom_functions(raw: Any, report: Report) -> List[Dict[str, Any]]:
    out = []
    for i, item in enumerate(expect_list(raw, report)):
        function = validate_entry(CustomFunctionModel, item, report, str(i))
        if function is not None:
            out.append(function.model_dump(mode="json"))
    return out


# ---- ~/.sirat/preferences.json and hardware_config.json (req 32) ------------------------------------------------

class PreferencesModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    value_format: Literal["hex", "dec", "bin"] = "hex"
    auto_read_on_click: bool = True
    show_secure_peripherals: bool = False
    confirm_critical_writes: bool = True
    dark_mode: bool = False
    last_position: int = Field(1, ge=1, le=4)
    watch_density: Literal["compact", "large"] = "compact"


class HardwareConfigModel(BaseModel):
    """Req 32 validation rules."""
    model_config = ConfigDict(extra="ignore")
    rpc_host: NonEmpty = "localhost"
    rpc_port: int = Field(10001, ge=1, le=65535)
    rpc_timeout: int = Field(5, ge=1, le=300)
    dut_position: int = Field(1, ge=1, le=4)
    rpc_override: bool = False


class SignalGeneratorModel(BaseModel):
    """Req 25 "Persistence File" (~/.sirat/signal_generator.json)."""
    model_config = ConfigDict(extra="ignore")
    sg_type: NonEmpty = "PacketSrw"
    input_config_name: str = "BLE_1M"
    frequency_mhz: float = Field(2440.0, gt=0, le=6000)
    power_dbm: float = Field(0.0, ge=-150, le=30)
    overrides: Dict[str, Any] = {}


class BlePacketModel(BaseModel):
    """Req 26 "Persistence File" (~/.sirat/ble_packet.json)."""
    model_config = ConfigDict(extra="ignore")
    access_address: Annotated[str, Field(pattern=r"^(0[xX])?[0-9a-fA-F]{1,8}$")] = "0x8E89BED6"
    crc_init: Annotated[str, Field(pattern=r"^(0[xX])?[0-9a-fA-F]{1,6}$")] = "0x555555"
    whitening_init: int = Field(37, ge=0, le=127)
    preamble: Annotated[str, Field(pattern=r"^(0[xX])?[0-9a-fA-F]{1,2}$")] = "0xAA"


def clean_signal_generator(raw: Any, report: Report) -> Dict[str, Any]:
    return validate_with_defaults(SignalGeneratorModel, raw, report).model_dump(mode="json")


def clean_ble_packet(raw: Any, report: Report) -> Dict[str, Any]:
    return validate_with_defaults(BlePacketModel, raw, report).model_dump(mode="json")


class MemoryViewerModel(BaseModel):
    """Req 19 "Persistence File" (~/.sirat/memory_viewer.json)."""
    model_config = ConfigDict(extra="ignore")
    last_address: Annotated[str, Field(pattern=r"^\s*((0[xX])?[0-9a-fA-F_]{1,10}|\d{1,10})\s*$")] = "0x20000000"


def clean_memory_viewer(raw: Any, report: Report) -> Dict[str, Any]:
    return validate_with_defaults(MemoryViewerModel, raw, report).model_dump(mode="json")


def clean_preferences(raw: Any, report: Report) -> Dict[str, Any]:
    return validate_with_defaults(PreferencesModel, raw, report).model_dump(mode="json")


def clean_hardware_config(raw: Any, report: Report) -> Dict[str, Any]:
    return validate_with_defaults(HardwareConfigModel, raw, report).model_dump(mode="json")
