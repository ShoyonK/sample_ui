"""Radio and PHY page, PRS card (req 24): pick signal, pin and channel; Apply Route; active routes with Remove."""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.prs import CHANNELS, CONSTRAINT_TEXT, DISABLE, PINS, allowed_channels, channel_problem
from sirat_ui.domains.radio.prs import PrsService
from sirat_ui.gateway.models import PrsRoute
from sirat_ui.shared.interactions import Alert, InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty


class PrsViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: PrsService, state: AppState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._interactions = interactions
        self._routes = DictListModel(["signal", "pin", "channel"], self)
        self._signal = ""
        self._pin = PINS[0]
        self._channel = 0
        self._busy = False
        service.changed.connect(self._refresh)
        state.changed.connect(lambda *_: self.changed.emit())
        self._refresh()

    routes = pyqtProperty(QObject, lambda self: self._routes, constant=True)
    pins = pyqtProperty("QStringList", lambda self: PINS, constant=True)
    channels = pyqtProperty("QStringList", lambda self: [str(c) for c in CHANNELS], constant=True)
    constraintText = pyqtProperty(str, lambda self: CONSTRAINT_TEXT, constant=True)
    signalLabels = pyqtProperty("QStringList", lambda self: [s.label for s in self._signals()], notify=changed)
    sourceText = pyqtProperty(str, lambda self: self._service.source_text, notify=changed)
    pinIndex = pyqtProperty(int, lambda self: PINS.index(self._pin), notify=changed)
    channelIndex = pyqtProperty(int, lambda self: self._channel, notify=changed)
    busy = qprop(bool, "_busy", changed)

    @pyqtProperty(int, notify=changed)
    def signalIndex(self) -> int:  # noqa: N802
        names = [s.name for s in self._signals()]
        return names.index(self._signal) if self._signal in names else -1

    @pyqtProperty(bool, notify=changed)
    def canRoute(self) -> bool:  # noqa: N802
        return self._state.can("rf.prs_route") and not self._busy and self._signal not in ("", DISABLE)

    @pyqtProperty(bool, notify=changed)
    def invalid(self) -> bool:
        return channel_problem(self._pin, self._channel) is not None

    @pyqtProperty(str, notify=changed)
    def hint(self) -> str:
        allowed = allowed_channels(self._pin)
        text = f"Port {self._pin[1]} uses channels {allowed[0]}-{allowed[-1]}"
        return text + f"; channel {self._channel} won't work" if self.invalid else text

    def _signals(self):
        return [s for s in self._service.signals if s.name != DISABLE]

    def _refresh(self) -> None:
        signals = self._signals()
        if signals and self._signal not in [s.name for s in signals]:
            self._signal = signals[0].name
        self._routes.set_items([{"signal": r.signal, "pin": r.pin, "channel": r.channel}
                                for r in self._service.routes])
        self.changed.emit()

    def _route(self) -> PrsRoute:
        return PrsRoute(self._signal, self._pin, self._channel)

    # ---- choices -------------------------------------------------------------------------------------

    @pyqtSlot(int)
    def setSignal(self, index: int) -> None:  # noqa: N802
        signals = self._signals()
        if 0 <= index < len(signals):
            self._signal = signals[index].name
            self.changed.emit()

    @pyqtSlot(int)
    def setPin(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(PINS):
            self._pin = PINS[index]
            self.changed.emit()

    @pyqtSlot(int)
    def setChannel(self, index: int) -> None:  # noqa: N802
        if index in CHANNELS:
            self._channel = index
            self.changed.emit()

    # ---- apply / remove / add to actions ---------------------------------------------------------------

    def _valid(self, route: PrsRoute) -> bool:
        if self._service.problem(route):
            self._interactions.alert(Alert("Invalid Port/Channel Combination", CONSTRAINT_TEXT, "warning"))
            return False
        return True

    @pyqtSlot()
    def apply(self) -> None:
        route = self._route()
        if not self.canRoute or not self._valid(route):
            return
        self._update(busy=True)

        def done(_: None) -> None:
            self._update(busy=False)
            self._interactions.toast("success", f"Successfully routed {route.signal} to {route.pin} "
                                                f"via PRS channel {route.channel}")

        self._service.apply(route).then(done, lambda _: self._update(busy=False))

    @pyqtSlot(int)
    def remove(self, row: int) -> None:
        if not 0 <= row < len(self._service.routes):
            return
        route = self._service.routes[row]
        self._service.remove(route).then(lambda _: self._interactions.toast(
            "success", f"Removed {route.signal} from {route.pin} (PRS channel {route.channel})"))

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        route = self._route()
        if self._signal in ("", DISABLE) or not self._valid(route):
            return
        action = self._service.add_action(route)
        self._interactions.toast("success", f"Added {action.name} to Actions")

    def current_route(self) -> PrsRoute:
        return self._route()


__all__: List[str] = ["PrsViewModel"]
