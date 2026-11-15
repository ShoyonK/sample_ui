"""The Station API's error codes and ApiError (docs/STATION_API.md "Errors")."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """The Station API's error codes. On the wire each is a JSON-RPC error's `data.reason` (jsonrpc.CODES has the
    integer `code` for each)."""
    WRONG_STATE = "wrong_state"
    INVALID_PARAMS = "invalid_params"
    UNKNOWN_METHOD = "unknown_method"
    TIMEOUT = "timeout"
    BUSY = "busy"
    CLAIMED = "claimed"
    CONFIRMATION_REQUIRED = "confirmation_required"
    READ_SENSITIVE = "read_sensitive"
    ACCESS_DENIED = "access_denied"
    OUT_OF_RANGE = "out_of_range"
    NOT_FOUND = "not_found"
    DUT_DISCONNECTED = "dut_disconnected"
    INSTRUMENT_ERROR = "instrument_error"
    HARDWARE_ERROR = "hardware_error"
    ABORTED = "aborted"
    INTERNAL = "internal"


class ApiError(Exception):
    """An error from the Station API: a code, a message (the code's name when there's none), and machine-readable
    `data` such as `missing` (WRONG_STATE) or `still_running` (TIMEOUT)."""

    def __init__(self, code: ErrorCode, message: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message or code.value)
        self.code = code
        self.message = message or code.value
        self.data: Dict[str, Any] = dict(data or {})

    def __repr__(self) -> str:
        return f"ApiError({self.code.value!r}, {self.message!r}, {self.data!r})"

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> Any:
        """How validation (validate.py) reads an error inside a result or event: a JSON-RPC error object,
        {code, message, data}. pydantic is imported here, not at the top, so code that only raises ApiError
        doesn't need it."""
        from pydantic_core import core_schema

        from station_protocol.jsonrpc import api_error

        def validate(value: Any) -> "ApiError":
            if isinstance(value, ApiError):
                return value
            if not isinstance(value, dict) or not isinstance(value.get("message", ""), str):
                raise ValueError("must be an error object {code, message, data}")
            return api_error(value)

        return core_schema.no_info_plain_validator_function(validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: Any, handler: Any) -> Dict[str, Any]:
        """The error object's JSON Schema (station_api.schema.json)."""
        return {"type": "object", "title": "Error",
                "properties": {"code": {"type": "integer"}, "message": {"type": "string"},
                               "data": {"type": "object", "properties": {"reason": {"type": "string"}},
                                        "required": ["reason"]}},
                "required": ["code", "message", "data"]}
