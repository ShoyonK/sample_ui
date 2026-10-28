"""ErrorPresenter: the one place that turns ApiError codes into user-facing wording (API doc: "Mapping rules")."""

from __future__ import annotations

from sirat_ui.core.requires import describe_missing
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.shared.interactions import Alert, InteractionService
from sirat_ui.domains.logs.service import LogService

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


class ErrorPresenter:
    def __init__(self, interactions: InteractionService, log: LogService) -> None:
        self._interactions = interactions
        self._log = log

    def message_for(self, error: ApiError) -> str:
        if error.code == ErrorCode.WRONG_STATE:
            missing = error.data.get("missing") or []
            return f"That needs {describe_missing(missing)} first." if missing else error.message
        template = _MESSAGES.get(error.code, "{message}")
        return template.format(message=error.message)

    def present(self, error: ApiError, context: str = "") -> None:
        prefix = f"{context}: " if context else ""
        self._log.error(prefix + error.message)
        if error.code == ErrorCode.ABORTED:
            return
        if error.code == ErrorCode.VERIFY_FAILED:
            written, readback = error.data.get("written", 0), error.data.get("readback", 0)
            self._interactions.alert(Alert(
                "Write verification failed",
                f"Written value: 0x{written:08X}\nRead-back value: 0x{readback:08X}\n\n"
                "This may be normal if the register has read-only bits or hardware overrides.",
            ))
            return
        self._interactions.toast("error", prefix + self.message_for(error))
