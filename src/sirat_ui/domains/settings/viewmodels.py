"""Settings page: preferences, user settings (export/import/clear, req 2), About (req 2), hardware config (req 32)."""

from __future__ import annotations

import logging

import platform
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QObject, QTimer, pyqtSignal, pyqtSlot

from sirat_ui import __version__
from sirat_ui.domains.settings.hardware import HardwareConfig, HardwareConfigService, validate
from sirat_ui.domains.settings.transfer import SettingsTransfer
from sirat_ui.shared.interactions import ConfirmRequest, InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

STATUS_RESET_MS = 3000

log = logging.getLogger("SiRAT.settings")


class SettingsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, state: AppState, on_clear_cache: Callable[[], None], transfer: SettingsTransfer,
                 interactions: InteractionService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = state
        self._on_clear_cache = on_clear_cache
        self._transfer = transfer
        self._interactions = interactions
        self._refresh()
        state.preferences_changed.connect(lambda _: self._refresh())
        state.changed.connect(self._refresh)

    darkMode = qprop(bool, "_dark_mode", changed)
    autoRead = qprop(bool, "_auto_read", changed)
    confirmCritical = qprop(bool, "_confirm_critical", changed)
    showSecure = qprop(bool, "_show_secure", changed)
    aboutRows = qprop("QVariantList", "_about_rows", changed)

    def _refresh(self) -> None:
        p, s = self._state.preferences, self._state
        about = [
            {"key": "SiRAT", "value": __version__},
            {"key": "Station service", "value": s.release_id or "not connected"},
            {"key": "Protocol", "value": str(s.protocol) if s.protocol is not None else "—"},
            {"key": "Backend", "value": s.backend_label or "—"},
            {"key": "Python", "value": platform.python_version()},
            {"key": "Qt / PyQt", "value": f"{QT_VERSION_STR} / {PYQT_VERSION_STR}"},
        ]
        self._update(dark_mode=p.dark_mode, auto_read=p.auto_read_on_click,
                     confirm_critical=p.confirm_critical_writes, show_secure=p.show_secure_peripherals,
                     about_rows=about)

    # ---- preferences -------------------------------------------------------------------------------

    @pyqtSlot(bool)
    def setDarkMode(self, on: bool) -> None:  # noqa: N802
        self._state.update_preferences(dark_mode=on)

    @pyqtSlot(bool)
    def setAutoRead(self, on: bool) -> None:  # noqa: N802
        self._state.update_preferences(auto_read_on_click=on)

    @pyqtSlot(bool)
    def setConfirmCritical(self, on: bool) -> None:  # noqa: N802
        self._state.update_preferences(confirm_critical_writes=on)

    @pyqtSlot(bool)
    def setShowSecure(self, on: bool) -> None:  # noqa: N802
        self._state.update_preferences(show_secure_peripherals=on)

    @pyqtSlot()
    def clearRegisterCache(self) -> None:  # noqa: N802
        self._on_clear_cache()
        self._interactions.toast("info", "Register cache cleared")

    # ---- user settings (req 2 File menu) -------------------------------------------------------

    @pyqtSlot()
    def exportSettings(self) -> None:  # noqa: N802
        def chosen(path) -> None:
            if not path:
                return
            try:
                names = self._transfer.export(Path(path))
                self._interactions.toast("success", f"Exported {len(names)} settings files to {path}")
            except OSError as exc:
                self._interactions.toast("error", f"Couldn't export: {exc}")

        name = f"sirat_settings_{time.strftime('%Y%m%d')}.json"
        self._interactions.choose_save_file("Export user settings", name, "JSON files (*.json)").then(chosen)

    @pyqtSlot()
    def importSettings(self) -> None:  # noqa: N802
        def chosen(path) -> None:
            if not path:
                return
            request = ConfirmRequest("Import user settings",
                                     f"This replaces your favorites, notes, formulas, actions, sequences, watch list, "
                                     f"logger, preferences and hardware configuration with the ones in {Path(path).name}.",
                                     confirm_text="Import", tone="danger")
            self._interactions.confirm(request).then(lambda answer: do_import(path) if answer.accepted else None)

        def do_import(path) -> None:
            try:
                names, skipped = self._transfer.import_(Path(path))
                if skipped:
                    for problem in skipped:
                        log.warning("Import skipped %s", problem)
                    self._interactions.toast("warning", f"Imported {len(names)} settings files; skipped "
                                                        f"{len(skipped)} invalid entries (details in the log)")
                else:
                    self._interactions.toast("success", f"Imported {len(names)} settings files")
            except ValueError as exc:
                self._interactions.toast("error", str(exc))

        self._interactions.choose_open_file("Import user settings", "JSON files (*.json)").then(chosen)

    @pyqtSlot()
    def clearAllSettings(self) -> None:  # noqa: N802
        request = ConfirmRequest("Clear all user settings",
                                 "This resets favorites, notes, formulas, actions, sequences, watch list, logger, "
                                 "preferences and hardware configuration to their defaults. You can't undo it; "
                                 "export first if you might want them back.",
                                 confirm_text="Clear everything", tone="danger")

        def answered(answer) -> None:
            if answer.accepted:
                self._transfer.clear_all()
                self._interactions.toast("info", "All user settings cleared")

        self._interactions.confirm(request).then(answered)


class HardwareConfigViewModel(BaseViewModel):
    """Req 32: edit, validate (red border + disabled Save), save, test; status text resets after 3 s."""

    changed = pyqtSignal()

    def __init__(self, service: HardwareConfigService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._errors: Dict[str, str] = {}
        self._host = ""
        self._port = ""
        self._timeout = ""
        self._position = ""
        self._override = False
        self._status = "Modify settings and click Save"
        self._status_level = "mute"
        self._busy = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(STATUS_RESET_MS)
        self._timer.timeout.connect(lambda: self._set_status("Modify settings and click Save", "mute", reset=False))
        self._load()
        service.config_changed.connect(self._load)

    host = qprop(str, "_host", changed)
    port = qprop(str, "_port", changed)
    timeout = qprop(str, "_timeout", changed)
    position = qprop(str, "_position", changed)
    override = qprop(bool, "_override", changed)
    statusText = qprop(str, "_status", changed)
    statusLevel = qprop(str, "_status_level", changed)
    busy = qprop(bool, "_busy", changed)

    @pyqtProperty("QVariantMap", notify=changed)
    def errors(self):
        return dict(self._errors)

    @pyqtProperty(bool, notify=changed)
    def canSave(self) -> bool:  # noqa: N802
        return not self._errors and not self._busy

    def _load(self) -> None:
        c = self._service.config
        self._update(host=c.rpc_host, port=str(c.rpc_port), timeout=str(c.rpc_timeout), position=str(c.dut_position),
                     override=c.rpc_override)
        self._validate()

    def _validate(self) -> None:
        self._errors = validate(self._host, self._port, self._timeout, self._position, self._override)
        self.changed.emit()

    def _set_status(self, text: str, level: str, reset: bool = True) -> None:
        self._update(status=text, status_level=level)
        if reset:
            self._timer.start()

    def _config(self) -> HardwareConfig:
        try:
            port = int(self._port)
        except ValueError:  # only reachable when the override is off and the port isn't checked
            port = self._service.config.rpc_port
        return HardwareConfig(self._host.strip(), port, int(self._timeout), int(self._position), self._override)

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name in ("host", "port", "timeout", "position"):
            self._update(**{name: value})
            self._validate()

    @pyqtSlot(bool)
    def setOverride(self, on: bool) -> None:  # noqa: N802
        self._update(override=on)
        self._validate()

    @pyqtSlot()
    def save(self) -> None:
        if self._errors:
            return
        self._service.save(self._config()).then(
            lambda _: self._set_status("Configuration saved successfully!", "ok"),
            lambda e: self._set_status(f"Saved, but the station refused the timeout: {e.message}", "danger", reset=False))

    @pyqtSlot()
    def testConnection(self) -> None:  # noqa: N802
        if self._errors:
            return
        self._update(busy=True, status="Testing connection…", status_level="mute")
        self._timer.stop()
        self.changed.emit()

        def ok(message: str) -> None:
            self._update(busy=False)
            self._set_status(message, "ok")

        def failed(error) -> None:
            self._update(busy=False)
            self._set_status(f"Connection failed: {error.message}", "danger", reset=False)

        self._service.test_connection(self._config()).then(ok, failed)
