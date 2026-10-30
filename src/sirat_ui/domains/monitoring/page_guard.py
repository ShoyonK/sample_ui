"""Stops the watch list and the data logger once nobody can see them.

They run while the Watch page, or a pop-out window showing them, is on screen. Leaving stops whatever just went out
of view; it doesn't start again by itself. Anything still in a pop-out window keeps running.
"""

from __future__ import annotations

from typing import Callable, List

from sirat_ui.domains.logs.service import LogService
from sirat_ui.domains.monitoring.logger import DataLoggerService
from sirat_ui.domains.monitoring.watch import WatchService
from sirat_ui.shared.interactions import InteractionService


class MonitoringGuard:
    def __init__(self, watch: WatchService, logger: DataLoggerService, log: LogService,
                 interactions: InteractionService, watch_on_screen: Callable[[], bool],
                 logger_on_screen: Callable[[], bool]) -> None:
        self._watch = watch
        self._logger = logger
        self._log = log
        self._interactions = interactions
        self._watch_on_screen = watch_on_screen
        self._logger_on_screen = logger_on_screen
        self._watch_seen = watch_on_screen()
        self._logger_seen = logger_on_screen()

    def check(self) -> None:
        """Call when the page or the set of pop-out windows changes. Only going out of view stops anything."""
        watch_seen, logger_seen = self._watch_on_screen(), self._logger_on_screen()
        stopped: List[str] = []
        if self._watch_seen and not watch_seen and self._watch.live:
            self._watch.stop()
            stopped.append("Watch list paused")
        if self._logger_seen and not logger_seen and self._logger.recording:
            self._logger.stop()
            stopped.append("data logger stopped")
        self._watch_seen, self._logger_seen = watch_seen, logger_seen
        if stopped:
            text = " and ".join(stopped)
            self._log.info(f"{text}: left the Watch page")
            self._interactions.toast("info", f"{text[0].upper()}{text[1:]}. Your data is kept.")
