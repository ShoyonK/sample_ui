"""ErrorPresenter: the one place that turns ApiError codes into user-facing wording (API doc: "Mapping rules")."""

from __future__ import annotations

from typing import Protocol

from sibench_ui.core.requires import describe_missing
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.models.dialogs import Alert
from sibench_ui.shared.interactions import InteractionService

_MESSAGES = {
    ErrorCode.TIMEOUT: "The station didn't answer in time.",
    ErrorCode.BUSY: "The DUT is busy with another operation. Try again when it's idle.",
    ErrorCode.CLAIMED: "Another user holds this station right now.",
    ErrorCode.ACCESS_DENIED: "{message}",
    ErrorCode.OUT_OF_RANGE: "{message}",
    ErrorCode.NOT_FOUND: "{message}",
    ErrorCode.READ_SENSITIVE: "{message}. Reading it clears FIFOs or flags, so it's skipped.",
    ErrorCode.DUT_DISCONNECTED: "The DUT connection dropped.",
    ErrorCode.INSTRUMENT_ERROR: "The instrument reported an error: {message}",
    ErrorCode.HARDWARE_ERROR: "The hardware reported an error. Recover the DUT to return to a safe state.",
    ErrorCode.ABORTED: "Stopped.",
    ErrorCode.INVALID_PARAMS: "{message}",
    ErrorCode.UNKNOWN_METHOD: "The station doesn't support this yet.",
    ErrorCode.INTERNAL: "Something went wrong in the station service. {message}",
}


class Log(Protocol):
    """What the presenter needs from the log (LogService implements it)."""

    def error(self, text: str) -> None: ...
    def warning(self, text: str) -> None: ...


class ErrorPresenter:
    """Shows API errors to the user: always a log line, and a toast unless the user stopped it themselves."""

    def __init__(self, interactions: InteractionService, log: Log) -> None:
        self._interactions = interactions
        self._log = log

    def message_for(self, error: ApiError) -> str:
        """The user-facing wording for an error (WRONG_STATE lists what's missing, in words)."""
        if error.code == ErrorCode.TIMEOUT and error.data.get("still_running"):
            return ("The station didn't answer in time. The call is still running there; "
                    "the log will say how it ended.")
        if error.code == ErrorCode.WRONG_STATE:
            missing = error.data.get("missing") or []
            return f"That needs {describe_missing(missing)} first." if missing else error.message
        template = _MESSAGES.get(error.code, "{message}")
        return template.format(message=error.message)

    def present(self, error: ApiError, context: str = "") -> None:
        """Logs the error and toasts it, prefixed with `context` ("Write CMU.CTRL: ..."). ABORTED is only logged."""
        prefix = f"{context}: " if context else ""
        self._log.error(prefix + error.message)
        if error.code == ErrorCode.ABORTED:
            return
        self._interactions.toast("error", prefix + self.message_for(error))

    def verify_mismatch(self, target: str, written: int, readback: int) -> None:
        """Req 7: the write happened but the read-back differs. A warning, not an error (WriteResult.verified)."""
        self._log.warning(f"Write {target}: read-back 0x{readback:X} differs from 0x{written:X}")
        self._interactions.alert(Alert(
            "Write verification failed",
            f"Written value: 0x{written:08X}\nRead-back value: 0x{readback:08X}\n\n"
            "This may be normal if the register has read-only bits or hardware overrides.",
        ))
