"""InteractionService: how services ask the user something without knowing QML exists.

DialogsViewModel implements it for the real UI; ScriptedInteractions answers in tests.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Protocol, Tuple

from sibench_ui.gateway.call import Call
from sibench_ui.models.dialogs import Alert, ConfirmAnswer, ConfirmRequest, PromptRequest


class InteractionService(Protocol):
    def confirm(self, request: ConfirmRequest) -> Call: ...       # -> ConfirmAnswer
    def prompt(self, request: PromptRequest) -> Call: ...         # -> dict | None (cancelled)
    def alert(self, alert: Alert) -> None: ...
    def toast(self, level: str, text: str) -> None: ...
    def choose_save_file(self, title: str, suggested: str, filters: str) -> Call: ...  # -> path str | None
    def choose_open_file(self, title: str, filters: str,
                         start_dir: Optional[Path] = None) -> Call: ...  # -> path str | None; opens in the home folder
    def show_code(self, title: str, code: str) -> None: ...       # req 16 code dialog


def save_text(interactions: InteractionService, title: str, suggested: str, filters: str,
              text: Callable[[], str], done: Callable[[str], str], encoding: str = "utf-8") -> Call:
    """Asks for a file name, writes the text there, and toasts how it went.

    Args:
        interactions: Where to ask and toast.
        title: The save dialog's title.
        suggested: The suggested file name or path.
        filters: The dialog's file type filter, e.g. "CSV files (*.csv)".
        text: Builds the text, called only once a path was chosen.
        done: The success toast for the chosen path.
        encoding: The file's encoding ("utf-8-sig" adds the BOM Excel wants for non-ASCII).

    Returns:
        The file dialog's call (resolved with the path, or None when cancelled).
    """
    def chosen(path: Optional[str]) -> None:
        if not path:
            return
        try:
            Path(path).write_text(text(), encoding=encoding)
        except OSError as exc:
            interactions.toast("error", f"Couldn't save: {exc}")
            return
        interactions.toast("success", done(path))

    return interactions.choose_save_file(title, suggested, filters).then(chosen)


class ScriptedInteractions:
    """Test double: queue answers with answer_next(); every request is recorded."""

    def __init__(self) -> None:
        self.confirms: List[ConfirmRequest] = []
        self.prompts: List[PromptRequest] = []
        self.alerts: List[Alert] = []
        self.toasts: List[Tuple[str, str]] = []
        self.codes: List[Tuple[str, str]] = []
        self.save_requests: List[Tuple[str, str]] = []
        self.open_requests: List[Tuple[str, Optional[Path]]] = []
        self._answers: Deque[Any] = deque()
        self._save_paths: Deque[Optional[str]] = deque()
        self._open_paths: Deque[Optional[str]] = deque()

    def answer_next(self, answer: Any) -> None:
        """Queues the answer to the next confirm or prompt. A bool becomes a ConfirmAnswer; with nothing queued,
        a confirm is declined and a prompt cancelled."""
        self._answers.append(answer)

    def confirm(self, request: ConfirmRequest) -> Call:
        self.confirms.append(request)
        answer = self._answers.popleft() if self._answers else False
        if isinstance(answer, bool):
            answer = ConfirmAnswer(answer)
        return Call.succeeded(answer)

    def prompt(self, request: PromptRequest) -> Call:
        self.prompts.append(request)
        answer: Optional[Dict[str, str]] = self._answers.popleft() if self._answers else None
        return Call.succeeded(answer)

    def alert(self, alert: Alert) -> None:
        self.alerts.append(alert)

    def toast(self, level: str, text: str) -> None:
        self.toasts.append((level, text))

    def answer_save(self, path: Optional[str]) -> None:
        self._save_paths.append(path)

    def choose_save_file(self, title: str, suggested: str, filters: str) -> Call:
        self.save_requests.append((title, suggested))
        return Call.succeeded(self._save_paths.popleft() if self._save_paths else None)

    def show_code(self, title: str, code: str) -> None:
        self.codes.append((title, code))

    def answer_open(self, path: Optional[str]) -> None:
        self._open_paths.append(path)

    def choose_open_file(self, title: str, filters: str, start_dir: Optional[Path] = None) -> Call:
        self.open_requests.append((title, start_dir))
        return Call.succeeded(self._open_paths.popleft() if self._open_paths else None)
