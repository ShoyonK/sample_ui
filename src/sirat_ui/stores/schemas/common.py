"""Field types shared by the file schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BeforeValidator, Field, StringConstraints
from typing_extensions import Annotated

_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RegisterName = Annotated[str, StringConstraints(strip_whitespace=True, pattern=rf"^{_IDENT}\.{_IDENT}$")]
FieldPath = Annotated[str, StringConstraints(strip_whitespace=True, pattern=rf"^{_IDENT}\.{_IDENT}\.{_IDENT}$")]
RegisterOrField = Annotated[str, StringConstraints(strip_whitespace=True,
                                                   pattern=rf"^{_IDENT}\.{_IDENT}(\.{_IDENT})?$")]


def to_int(value: Any) -> Any:
    """Accepts 5, "5" and "0x1F" (hand-edited files often use hex strings). bool isn't a number here."""
    if isinstance(value, bool):
        raise ValueError("expected a number, not true/false")
    if isinstance(value, str):
        try:
            return int(value.strip(), 0)
        except ValueError:
            raise ValueError(f"'{value}' isn't a number (use decimal or 0x hex)") from None
    return value


RegisterValue = Annotated[int, BeforeValidator(to_int), Field(ge=0, le=0xFFFFFFFF)]
