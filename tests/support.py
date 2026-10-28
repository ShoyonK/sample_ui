"""Harness: a wired app without a window (real container, fake station, scripted dialogs)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sirat_ui.app.container import ServiceContainer
from sirat_ui.gateway.fake import FakeStationGateway
from sirat_ui.gateway.scheduler import ManualScheduler
from sirat_ui.models.registers import ChipInfo
from sirat_ui.shared.interactions import ScriptedInteractions
from sirat_ui.stores.demo_data import seed_demo_data
from sirat_ui.stores.json_store import UserStores


class Harness:
    """A wired app without a window: the real container, fake station, scripted dialogs."""

    def __init__(self, home: Path, seed: bool = True, connect: bool = True, real_dialogs: bool = False,
                 chip: Optional[ChipInfo] = None) -> None:
        self.home = home
        if seed:
            seed_demo_data(UserStores.in_home(home))
        self.scheduler = ManualScheduler()
        self.fake = FakeStationGateway(self.scheduler)
        if chip is not None:  # e.g. an Everest chip for WiFi PHYs
            self.fake.chip = chip
        self.ix = ScriptedInteractions()
        # real_dialogs: E2E tests answer the actual QML dialogs; other tests script the answers
        self.container = ServiceContainer(self.fake, home, self.scheduler, "test", None if real_dialogs else self.ix)
        self.shell = self.container.shell
        self.state = self.container.state
        self.prefs = self.container.prefs
        self.selection = self.container.selection
        self.services = self.container.services
        self.container.start(autoconnect=connect)

    def register(self, name: str):
        reg = self.services.catalog.register(name)
        assert reg is not None, f"unknown register {name}"
        return reg

    def select(self, name: str, by_user: bool = True):
        reg = self.register(name)
        self.selection.select(reg, by_user=by_user)
        return reg

    def restart(self) -> "Harness":
        """Simulates closing and reopening the app with the same home folder."""
        return Harness(self.home, seed=False)
