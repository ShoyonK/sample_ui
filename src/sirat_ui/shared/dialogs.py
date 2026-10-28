"""DialogsViewModel: the QML-side implementation of InteractionService.

Services ask; this VM exposes the request as properties; DialogHost.qml shows it and answers via slots.
"""

from __future__ import annotations

import itertools
from collections import deque
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Optional, Tuple

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from sirat_ui.core.highlight import highlight_python
from sirat_ui.gateway.call import Call
from sirat_ui.models.dialogs import Alert, ConfirmAnswer, ConfirmRequest, PromptRequest
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, copy_to_clipboard, qprop

TOAST_MS = 3500


class DialogsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, is_dark: Callable[[], bool] = lambda: False,
                 chooser: Optional[Callable[[str, str, str], Optional[str]]] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._is_dark = is_dark
        self._chooser = chooser or _native_save_dialog
        self._opener = _native_open_dialog
        self._code: Dict[str, Any] = {}
        self._code_raw = ""
        self._confirm: Dict[str, Any] = {}
        self._prompt: Dict[str, Any] = {}
        self._alert: Dict[str, Any] = {}
        self._confirm_queue: Deque[Tuple[Dict[str, Any], Call]] = deque()
        self._confirm_call: Optional[Call] = None
        self._prompt_call: Optional[Call] = None
        self._ids = itertools.count(1)
        self._toasts = DictListModel(["toastId", "level", "text"], self)

    confirm = qprop("QVariantMap", "_confirm", changed)
    prompt = qprop("QVariantMap", "_prompt", changed)
    alert = qprop("QVariantMap", "_alert", changed)
    code = qprop("QVariantMap", "_code", changed)

    @pyqtProperty(QObject, constant=True)
    def toasts(self) -> DictListModel:
        return self._toasts

    # ---- InteractionService ---------------------------------------------------------------

    def confirm_request(self, request: ConfirmRequest) -> Call:
        call: Call = Call()
        data = {
            "title": request.title, "message": request.message, "warning": request.warning,
            "confirmText": request.confirm_text, "allowDontShow": request.allow_dont_show, "tone": request.tone,
            "details": [{"key": k, "value": v} for k, v in request.details],
        }
        self._confirm_queue.append((data, call))
        if self._confirm_call is None:
            self._show_next_confirm()
        return call

    def prompt_request(self, request: PromptRequest) -> Call:
        if self._prompt_call is not None:
            self._prompt_call.resolve(None)
        self._prompt_call = Call()
        self._update(prompt={
            "title": request.title, "message": request.message, "confirmText": request.confirm_text,
            "fields": [{"key": f.key, "label": f.label, "value": f.value, "placeholder": f.placeholder,
                        "options": list(f.options), "multiline": f.multiline} for f in request.fields],
        })
        return self._prompt_call

    def show_alert(self, alert: Alert) -> None:
        self._update(alert={"title": alert.title, "message": alert.message, "level": alert.level})

    def show_toast(self, level: str, text: str) -> None:
        toast_id = next(self._ids)
        self._toasts.set_items((self._toasts.items + [{"toastId": toast_id, "level": level, "text": text}])[-4:])
        # The timer is a child of this VM, so it dies with it instead of firing into a deleted model.
        timer = QTimer(self)
        timer.setSingleShot(True)
        def expire() -> None:
            self.dismissToast(toast_id)
            timer.deleteLater()

        timer.timeout.connect(expire)
        timer.start(TOAST_MS)

    def choose_save_file(self, title: str, suggested: str, filters: str) -> Optional[str]:
        return self._chooser(title, suggested, filters)

    def choose_open_file(self, title: str, filters: str) -> Optional[str]:
        return self._opener(title, filters)

    def show_code_dialog(self, title: str, code: str) -> None:
        self._code_raw = code
        self._update(code={"title": title, "html": highlight_python(code, self._is_dark())})

    @pyqtSlot()
    def copyCode(self) -> None:  # noqa: N802
        copy_to_clipboard(self._code_raw)
        self.show_toast("info", "Code copied to the clipboard")

    @pyqtSlot()
    def saveCode(self) -> None:  # noqa: N802
        path = self.choose_save_file("Save generated code", "sirat_actions.py", "Python files (*.py)")
        if not path:
            return
        try:
            Path(path).write_text(self._code_raw, encoding="utf-8")
            self.show_toast("success", f"Saved {path}")
        except OSError as exc:
            self.show_toast("error", f"Couldn't save: {exc}")

    @pyqtSlot()
    def closeCode(self) -> None:  # noqa: N802
        self._update(code={})

    # ---- QML answers ------------------------------------------------------------------------

    @pyqtSlot(bool, bool)
    def answerConfirm(self, accepted: bool, dont_show_again: bool) -> None:  # noqa: N802 (QML API)
        call, self._confirm_call = self._confirm_call, None
        self._update(confirm={})
        if call:
            call.resolve(ConfirmAnswer(accepted, dont_show_again))
        self._show_next_confirm()

    @pyqtSlot("QVariantMap")
    def submitPrompt(self, values: Dict[str, Any]) -> None:  # noqa: N802
        call, self._prompt_call = self._prompt_call, None
        self._update(prompt={})
        if call:
            call.resolve({k: str(v) for k, v in values.items()})

    @pyqtSlot()
    def cancelPrompt(self) -> None:  # noqa: N802
        call, self._prompt_call = self._prompt_call, None
        self._update(prompt={})
        if call:
            call.resolve(None)

    @pyqtSlot()
    def dismissAlert(self) -> None:  # noqa: N802
        self._update(alert={})

    @pyqtSlot(int)
    def dismissToast(self, toast_id: int) -> None:  # noqa: N802
        self._toasts.set_items([t for t in self._toasts.items if t["toastId"] != toast_id])

    def _show_next_confirm(self) -> None:
        if self._confirm_queue:
            data, self._confirm_call = self._confirm_queue.popleft()
            self._update(confirm=data)


class QmlInteractions:
    """Adapts DialogsViewModel to the InteractionService protocol used by services."""

    def __init__(self, dialogs: DialogsViewModel) -> None:
        self._dialogs = dialogs

    def confirm(self, request: ConfirmRequest) -> Call:
        return self._dialogs.confirm_request(request)

    def prompt(self, request: PromptRequest) -> Call:
        return self._dialogs.prompt_request(request)

    def alert(self, alert: Alert) -> None:
        self._dialogs.show_alert(alert)

    def toast(self, level: str, text: str) -> None:
        self._dialogs.show_toast(level, text)

    def choose_save_file(self, title: str, suggested: str, filters: str) -> Call:
        return Call.succeeded(self._dialogs.choose_save_file(title, suggested, filters))

    def show_code(self, title: str, code: str) -> None:
        self._dialogs.show_code_dialog(title, code)

    def choose_open_file(self, title: str, filters: str) -> Call:
        return Call.succeeded(self._dialogs.choose_open_file(title, filters))


def _native_save_dialog(title: str, suggested: str, filters: str) -> Optional[str]:
    """The Windows save dialog. Modal; returns None when cancelled."""
    from PyQt5.QtWidgets import QFileDialog  # needs the QApplication the app always creates
    path, _ = QFileDialog.getSaveFileName(None, title, str(Path.home() / suggested), filters)
    return path or None


def _native_open_dialog(title: str, filters: str) -> Optional[str]:
    """The Windows open dialog. Modal; returns None when cancelled."""
    from PyQt5.QtWidgets import QFileDialog
    path, _ = QFileDialog.getOpenFileName(None, title, str(Path.home()), filters)
    return path or None
