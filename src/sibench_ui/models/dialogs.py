"""What a service asks the user through a dialog: confirmations, prompts and alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ConfirmRequest:
    """The confirmation dialog: title, message, key/value details, an optional warning box, and the button."""
    title: str
    message: str
    details: List[Tuple[str, str]] = field(default_factory=list)
    warning: str = ""
    confirm_text: str = "Confirm"
    allow_dont_show: bool = False
    tone: str = "warning"  # warning | danger | info


@dataclass
class ConfirmAnswer:
    """The user's answer to a ConfirmRequest."""
    accepted: bool
    dont_show_again: bool = False


@dataclass
class PromptField:
    """One field of a prompt; non-empty options make it a drop-down."""
    key: str
    label: str
    value: str = ""
    placeholder: str = ""
    options: List[str] = field(default_factory=list)  # non-empty: shown as a drop-down
    multiline: bool = False


@dataclass
class PromptRequest:
    """The prompt dialog: one or more fields; the answer is {field key: text}, or None when cancelled."""
    title: str
    fields: List[PromptField]
    message: str = ""
    confirm_text: str = "Save"


@dataclass
class Alert:
    """A modal message with an OK button. level: warning | error | info."""
    title: str
    message: str
    level: str = "warning"
