"""On-disk formats of the original SiRAT settings files (sirat_requirements.txt, DATA REQUIREMENTS).

Readers accept the original format and the plain-list format earlier builds of this frontend wrote,
so nothing already saved is lost. Writers always produce the original format, so the old and new GUIs
can share one home folder.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


def _names(value: Any) -> List[str]:
    return [n for n in value if isinstance(n, str)] if isinstance(value, list) else []


def _rate(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---- ~/.sirat_favorites.json (req 8): {"favorites": [...]} -----------------------------------

def read_favorites(raw: Any) -> List[str]:
    return _names(raw.get("favorites") if isinstance(raw, dict) else raw)


def write_favorites(names: List[str]) -> Dict[str, Any]:
    return {"favorites": list(names)}


# ---- ~/.sirat_watch_list.json (req 18): {"watched_fields": [...], "refresh_rate": 1.0} --------

def read_watch_list(raw: Any) -> Tuple[List[str], float]:
    if isinstance(raw, dict):
        return _names(raw.get("watched_fields")), _rate(raw.get("refresh_rate"), 1.0)
    return _names(raw), 1.0


def write_watch_list(names: List[str], refresh_rate: float) -> Dict[str, Any]:
    return {"watched_fields": list(names), "refresh_rate": refresh_rate}


# ---- ~/.sirat_data_logger.json (req 17): {"tracked_fields": [...], "sample_rate": 1.0} --------

def read_data_logger(raw: Any) -> Tuple[List[str], float]:
    if not isinstance(raw, dict):
        return [], 1.0
    names = raw.get("tracked_fields", raw.get("fields"))
    return _names(names), _rate(raw.get("sample_rate", raw.get("rate_s")), 1.0)


def write_data_logger(names: List[str], sample_rate: float) -> Dict[str, Any]:
    return {"tracked_fields": list(names), "sample_rate": sample_rate}


# ---- ~/.sirat_sequences.json (req 14): {name: {"action_names": [...], "description": ""}} -----

@dataclass
class SequenceRecord:
    action_names: List[str] = field(default_factory=list)
    description: str = ""


def read_sequences(raw: Any) -> "OrderedDict[str, SequenceRecord]":
    sequences: "OrderedDict[str, SequenceRecord]" = OrderedDict()
    if not isinstance(raw, dict):
        return sequences
    for name, value in raw.items():
        if isinstance(value, dict):
            sequences[name] = SequenceRecord(_names(value.get("action_names")), str(value.get("description") or ""))
        elif isinstance(value, list):
            sequences[name] = SequenceRecord(_names(value))
    return sequences


def write_sequences(sequences: "OrderedDict[str, SequenceRecord]") -> Dict[str, Any]:
    return {name: {"action_names": list(r.action_names), "description": r.description}
            for name, r in sequences.items()}


# ---- ~/.sirat/field_formulas.json (req 11): {name: {"formula": "...", "unit": "Hz"}} -----------

def read_formulas(raw: Any) -> Dict[str, Tuple[str, str]]:
    formulas: Dict[str, Tuple[str, str]] = {}
    if not isinstance(raw, dict):
        return formulas
    for name, value in raw.items():
        if isinstance(value, dict) and value.get("formula"):
            formulas[name] = (str(value["formula"]), str(value.get("unit") or ""))
        elif isinstance(value, (list, tuple)) and value:  # earlier builds wrote [formula, unit]
            formulas[name] = (str(value[0]), str(value[1]) if len(value) > 1 else "")
    return formulas


def write_formulas(formulas: Dict[str, Tuple[str, str]]) -> Dict[str, Any]:
    return {name: {"formula": expr, "unit": unit} for name, (expr, unit) in formulas.items()}


# ---- ~/.sirat_custom_functions.json (req 15): [{"name": "...", "code": "..."}] -------------------

def read_custom_functions(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, list):
        return {}
    return {str(item["name"]): str(item.get("code") or "") for item in raw
            if isinstance(item, dict) and item.get("name")}
