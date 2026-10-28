"""What a service asks the user through a dialog: confirmations, prompts and alerts."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import List, Tuple


@dataclass
class ConfirmRequest:
    title: str
    message: str
    details: List[Tuple[str, str]] = field(default_factory=list)
    warning: str = ""
    confirm_text: str = "Confirm"
    allow_dont_show: bool = False
    tone: str = "warning"  # warning | danger | info


@dataclass
class ConfirmAnswer:
    accepted: bool
    dont_show_again: bool = False


@dataclass
class PromptField:
    key: str
    label: str
    value: str = ""
    placeholder: str = ""
    options: List[str] = field(default_factory=list)  # non-empty: shown as a drop-down
    multiline: bool = False


@dataclass
class PromptRequest:
    title: str
    fields: List[PromptField]
    message: str = ""
    confirm_text: str = "Save"


@dataclass
class Alert:
    title: str
    message: str
    level: str = "warning"
