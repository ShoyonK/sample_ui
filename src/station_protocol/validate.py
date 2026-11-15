"""Validating JSON against the protocol's types (pydantic, strict JSON mode).

validate(type, data) checks parsed JSON against a type from this package (a dataclass, a TypedDict, a list of
them, a ranged int...) and returns it built as that type. It raises ValidationFailed, naming where the JSON
doesn't fit ("phy.config.channel: must be a whole number").

Strict JSON mode is the wire's rule exactly: an array is accepted for a tuple and a whole number for a float,
unknown keys in objects are ignored (so a newer peer can add fields), but "5" or true where a number belongs is
an error. A server refuses unknown *parameters* separately (methods.check_params).
"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import TypeAdapter, ValidationError
from pydantic_core import to_json


class ValidationFailed(ValueError):
    """JSON that doesn't match the expected type; `path` says where (e.g. "phy.config.channel")."""

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path or 'value'}: {message}")
        self.path = path


_adapters: Dict[Any, TypeAdapter] = {}


def adapter(tp: Any) -> TypeAdapter:
    """The (cached) pydantic TypeAdapter for a type."""
    try:
        cached = _adapters.get(tp)
    except TypeError:   # an unhashable type (e.g. Annotated with a Field): build it each time
        return TypeAdapter(tp)
    if cached is None:
        cached = _adapters[tp] = TypeAdapter(tp)
    return cached


def validate(tp: Any, data: Any, path: str = "") -> Any:
    """`data` (parsed JSON) validated as type `tp`. `path` prefixes the location in errors. Raises
    ValidationFailed."""
    if tp is Any:
        return data
    try:
        # JSON mode is the wire's strictness; the parsed value goes back to JSON text for it (cheap: the
        # biggest messages are the register tree, ~35 KB, and ECA pages, one base64 string per channel)
        return adapter(tp).validate_json(to_json(data), strict=True)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join([path] * bool(path) + [_part(p) for p in first["loc"]]).replace(".[", "[")
        raise ValidationFailed(where, _message(first)) from None


def _part(loc: Any) -> str:
    return f"[{loc}]" if isinstance(loc, int) else str(loc)


# pydantic's error types -> the wording the other wire errors use
_MESSAGES = {
    "missing": "is required",
    "int_type": "must be a whole number",
    "int_from_float": "must be a whole number",
    "float_type": "must be a number",
    "bool_type": "must be true or false",
    "string_type": "must be a string",
    "list_type": "must be an array",
    "tuple_type": "must be an array",
    "dict_type": "must be an object",
    "dataclass_type": "must be an object",
    "model_type": "must be an object",
    "typed_dict_type": "must be an object",
    "none_required": "must be null",
}


def _message(error: Any) -> str:
    kind = error["type"]
    if kind in _MESSAGES:
        return _MESSAGES[kind]
    if kind in ("union_tag_invalid", "union_tag_not_found"):
        ctx = error.get("ctx") or {}
        tag, expected = ctx.get("discriminator", "tag"), ctx.get("expected_tags", "")
        tag = str(tag).strip("'")
        return f"{tag} must be one of {expected}" if expected else f"{tag} is required"
    text = str(error["msg"])
    return text[:1].lower() + text[1:]
