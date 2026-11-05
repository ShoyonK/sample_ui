"""The last line of defence: an unexpected Python error is logged and shown, and the app keeps running.

Without it PyQt aborts on an exception in a slot, so one bug in a click handler closes SiRAT and loses the
session. Installed by the launchers only, never under pytest: pytest-qt has its own hook that fails the test.
"""

from __future__ import annotations

import logging
import sys
import traceback
from types import TracebackType
from typing import Callable, Optional, Type

from sirat_ui.domains.logs.service import LogService
from sirat_ui.shared.interactions import InteractionService

Hook = Callable[[Type[BaseException], BaseException, Optional[TracebackType]], None]


def make_hook(log: LogService, interactions: InteractionService) -> Hook:
    def hook(exc_type: Type[BaseException], exc: BaseException, tb: Optional[TracebackType]) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        try:
            details = "".join(traceback.format_exception(exc_type, exc, tb))
            logging.getLogger("SiRAT.crash").error("Unexpected error\n%s", details)   # full traceback: session log
            log.error(f"Unexpected error: {exc_type.__name__}: {exc}")
            interactions.toast("error", f"Something went wrong ({exc_type.__name__}: {exc}). "
                                        "SiRAT is still running; details are in the session log.")
        except Exception:  # reporting must never raise, or we're back to aborting
            sys.__excepthook__(exc_type, exc, tb)
    return hook


def install(log: LogService, interactions: InteractionService) -> None:
    sys.excepthook = make_hook(log, interactions)
