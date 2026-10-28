"""RegisterService: read/write workflows (req §5, §7).

Owns: access checks, critical-write confirmation, write verification, the value cache,
change detection (previous values) and history recording.
"""

from __future__ import annotations

from typing import Dict, Optional

from sirat_ui.core.observable import Event
from sirat_ui.core.registers import FieldDef, RegisterDef
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.models import WriteResult
from sirat_ui.gateway.port import StationGateway
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.domains.history.service import HistoryLog
from sirat_ui.shared.interactions import ConfirmAnswer, ConfirmRequest, InteractionService
from sirat_ui.domains.logs.service import LogService
from sirat_ui.state.app_state import AppState

CRITICAL_WARNING = ("This is a critical peripheral. Writing incorrect values may cause device lockup "
                    "or debug access loss.")


class RegisterService:
    def __init__(self, gateway: StationGateway, state: AppState, history: HistoryLog,
                 interactions: InteractionService, errors: ErrorPresenter, log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._history = history
        self._interactions = interactions
        self._errors = errors
        self._log = log
        self.values: Dict[str, int] = {}
        self.previous: Dict[str, int] = {}
        self.value_changed = Event()  # (full_name, value)

    # ---- cache -------------------------------------------------------------

    def cached(self, full_name: str) -> Optional[int]:
        return self.values.get(full_name)

    def previous_value(self, full_name: str) -> Optional[int]:
        return self.previous.get(full_name)

    def clear_cache(self) -> None:
        self.values.clear()
        self.previous.clear()
        self.value_changed.emit("", None)

    def _store(self, full_name: str, value: int) -> None:
        if full_name in self.values:
            self.previous[full_name] = self.values[full_name]
        self.values[full_name] = value
        self.value_changed.emit(full_name, value)

    # ---- reads -----------------------------------------------------------------

    def read(self, reg: RegisterDef, manual: bool = True, quiet: bool = False) -> Call:
        """manual: record in history (req 9). quiet: log failures without a message per register (read all)."""
        if not reg.access.readable:
            error = ApiError(ErrorCode.ACCESS_DENIED, f"Cannot read write-only register {reg.full_name}")
            self._errors.present(error)
            return Call.failed(error)
        out: Call = Call()
        self._log.debug(f"Reading register {reg.full_name}")

        def ok(value: int) -> None:
            self._store(reg.full_name, value)
            if manual:
                self._history.record("READ", reg.full_name, value)
            self._state.set_status_message(f"{reg.full_name} @ 0x{reg.address:08X} · read ok")
            out.resolve(value)

        def failed(error: ApiError) -> None:
            self._state.set_status_message(f"{reg.full_name} @ 0x{reg.address:08X} · read failed")
            if quiet:
                self._log.warning(f"Read {reg.full_name}: {error.message}")
            else:
                self._errors.present(error, f"Read {reg.full_name}")
            out.reject(error)

        self._gateway.read_register(self._state.position, reg.full_name).then(ok, failed)
        return out

    # ---- writes ----------------------------------------------------------------

    def write(self, reg: RegisterDef, value: int) -> Call:
        if not reg.access.writable:
            return self._reject(ApiError(ErrorCode.ACCESS_DENIED, f"Cannot write read-only register {reg.full_name}"))
        if value < 0 or value > reg.max_value:
            return self._reject(ApiError(ErrorCode.OUT_OF_RANGE,
                                         f"Value 0x{value:X} out of range for {reg.full_name} (max: 0x{reg.max_value:X})"))
        return self._write(reg, None, value)

    def write_field(self, reg: RegisterDef, field: FieldDef, value: int) -> Call:
        if not field.access.writable:
            return self._reject(ApiError(ErrorCode.ACCESS_DENIED, f"Cannot write read-only field {field.full_name}"))
        if value < 0 or value > field.max_value:
            return self._reject(ApiError(ErrorCode.OUT_OF_RANGE,
                                         f"Value 0x{value:X} out of range for {field.full_name} (max: 0x{field.max_value:X})"))
        return self._write(reg, field, value)

    def toggle_bit(self, reg: RegisterDef, bit: int) -> Call:
        current = self.values.get(reg.full_name, reg.reset)
        return self.write(reg, current ^ (1 << bit))

    def _reject(self, error: ApiError) -> Call:
        self._errors.present(error)
        return Call.failed(error)

    def _write(self, reg: RegisterDef, field: Optional[FieldDef], value: int) -> Call:
        out: Call = Call()
        target = field.full_name if field else reg.full_name
        preconfirmed = reg.critical and not self._state.preferences.confirm_critical_writes

        def attempt(confirm: bool) -> None:
            pos = self._state.position
            self._log.debug(f"Writing {target} = 0x{value:X}" + (" (confirmed)" if confirm else ""))
            if field:
                call = self._gateway.write_field(pos, reg.full_name, field.name, value, confirm, True)
            else:
                call = self._gateway.write_register(pos, reg.full_name, value, confirm, True)
            call.then(done, failed)

        def record(readback: int) -> None:
            self._store(reg.full_name, readback)
            shown = field.extract(readback) if field else readback
            self._history.record("WRITE", reg.full_name, shown, field.name if field else None, readback)

        def done(result: WriteResult) -> None:
            record(result.readback)
            self._log.success(f"Wrote {target} = 0x{value:X} · verified")
            self._state.set_status_message(f"{target} @ 0x{reg.address:08X} · write ok")
            out.resolve(result)

        def failed(error: ApiError) -> None:
            if error.code == ErrorCode.CONFIRMATION_REQUIRED:
                self._interactions.confirm(self._confirm_request(reg, field, value)).then(answered)
                return
            if error.code == ErrorCode.VERIFY_FAILED and "readback" in error.data:
                record(int(error.data["readback"]))
            self._errors.present(error, f"Write {target}")
            out.reject(error)

        def answered(answer: ConfirmAnswer) -> None:
            if not answer.accepted:
                self._log.info(f"Write to {target} cancelled")
                out.reject(ApiError(ErrorCode.ABORTED, "Write cancelled"))
                return
            if answer.dont_show_again:
                self._state.update_preferences(confirm_critical_writes=False)
            attempt(True)

        attempt(preconfirmed)
        return out

    def _confirm_request(self, reg: RegisterDef, field: Optional[FieldDef], value: int) -> ConfirmRequest:
        current = self.values.get(reg.full_name)
        new_reg_value = field.insert(current or 0, value) if field else value
        details = [("Register", field.full_name if field else reg.full_name),
                   ("Address", f"0x{reg.address:08X}"),
                   ("Current", f"0x{current:08X}" if current is not None else "not read"),
                   ("New value", f"0x{new_reg_value:08X}")]
        return ConfirmRequest(
            title="Confirm write to critical register",
            message=f"{reg.peripheral} is a critical peripheral. Check the value before writing.",
            details=details, warning=CRITICAL_WARNING, confirm_text="Write", allow_dont_show=True,
        )
