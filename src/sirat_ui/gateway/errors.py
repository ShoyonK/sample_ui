"""Error codes from the Station API design doc ("Events and errors")."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
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
    def __init__(self, code: ErrorCode, message: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message or code.value)
        self.code = code
        self.message = message or code.value
        self.data: Dict[str, Any] = dict(data or {})

    def __repr__(self) -> str:
        return f"ApiError({self.code.value!r}, {self.message!r}, {self.data!r})"
