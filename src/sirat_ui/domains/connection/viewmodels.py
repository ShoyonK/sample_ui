"""Connect sheet and disconnect recovery dialog (req §3)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.connection.service import ConnectionService
from sirat_ui.domains.settings.hardware import HardwareConfigService
from sirat_ui.domains.logs.service import LogService
from sirat_ui.domains.radio.phy import WIFI_FAMILY
from sirat_ui.gateway.models import LogLine
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

CONFIG_TYPES = ["EFX", "EFR32"]


class ConnectionViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: ConnectionService, state: AppState, log: LogService,
                 hardware: Optional[HardwareConfigService] = None, interactions: Optional[InteractionService] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._hardware = hardware
        self._interactions = interactions
        self._override = False
        self._rpc_host = "localhost"
        self._rpc_port = "10001"
        self._sheet_open = False
        self._position = state.position
        self._config_type = "EFR32"
        self._config_file = ""
        self._busy = False
        self._connected = state.connected
        self._console = DictListModel(["level", "text"], self)
        log.added.connect(self._on_log)
        state.changed.connect(lambda: self._update(connected=state.connected, busy=state.connecting))

    sheetOpen = qprop(bool, "_sheet_open", changed)
    override = qprop(bool, "_override", changed)
    rpcHost = qprop(str, "_rpc_host", changed)
    rpcPort = qprop(str, "_rpc_port", changed)
    position = qprop(int, "_position", changed)
    configTypeIndex = pyqtProperty(int, lambda self: CONFIG_TYPES.index(self._config_type), notify=changed)
    configFile = qprop(str, "_config_file", changed)
    busy = qprop(bool, "_busy", changed)
    connected = qprop(bool, "_connected", changed)

    @pyqtProperty(QObject, constant=True)
    def console(self) -> DictListModel:
        return self._console

    def _on_log(self, line: LogLine) -> None:
        if self._sheet_open or self._busy:
            self._console.set_items((self._console.items + [{"level": line.level, "text": line.text}])[-200:])

    @pyqtSlot()
    def openSheet(self) -> None:  # noqa: N802
        """The address fields start from Settings (req 32 defaults); changes here apply to one connection."""
        values: Dict[str, Any] = dict(sheet_open=True, position=self._state.position)
        if self._hardware is not None:
            c = self._hardware.config
            values.update(override=c.rpc_override, rpc_host=c.rpc_host, rpc_port=str(c.rpc_port))
        self._update(**values)

    @pyqtSlot(bool)
    def setOverride(self, on: bool) -> None:  # noqa: N802
        self._update(override=on)

    @pyqtSlot(str)
    def setRpcHost(self, host: str) -> None:  # noqa: N802
        self._update(rpc_host=host)

    @pyqtSlot(str)
    def setRpcPort(self, port: str) -> None:  # noqa: N802
        self._update(rpc_port=port)

    def _address(self):
        """(host, port) to send, (None, None) for the workspace config, or raises ValueError."""
        if not self._override:
            return None, None
        host = self._rpc_host.strip()
        if not host:
            raise ValueError("Enter an RPC host, or uncheck \"Use a specific RPC address\"")
        try:
            port = int(self._rpc_port)
        except ValueError:
            raise ValueError("The RPC port must be a whole number") from None
        if not 1 <= port <= 65535:
            raise ValueError("The RPC port must be between 1 and 65535")
        return host, port

    @pyqtSlot()
    def closeSheet(self) -> None:  # noqa: N802
        self._update(sheet_open=False)

    @pyqtSlot(int)
    def setPosition(self, position: int) -> None:  # noqa: N802
        self._update(position=position)

    @pyqtSlot(int)
    def setConfigTypeIndex(self, index: int) -> None:  # noqa: N802
        self._update(config_type=CONFIG_TYPES[max(0, min(index, len(CONFIG_TYPES) - 1))])

    @pyqtSlot(str)
    def setConfigFile(self, path: str) -> None:  # noqa: N802
        self._update(config_file=path)

    @pyqtSlot()
    def connect(self) -> None:
        try:
            host, port = self._address()
        except ValueError as exc:
            self._console.set_items([{"level": "error", "text": str(exc)}])
            if self._interactions is not None:
                self._interactions.toast("error", str(exc))
            return
        address = f", rpc_host={host!r}, rpc_port={port}" if host else ""
        self._console.set_items([{"level": "info", "text": f"› dut.connect(position={self._position}, "
                                                           f"config_type={self._config_type}{address})"}])
        self._state.set_position(self._position)
        self._update(busy=True)
        self._service.connect(self._position, self._config_type, self._config_file, host, port).then(
            lambda _: self._update(busy=False), lambda _: self._update(busy=False))

    @pyqtSlot()
    def disconnectDut(self) -> None:  # noqa: N802 (not `disconnect`, which would shadow QObject.disconnect)
        self._service.disconnect(self._position)


class DisconnectRecoveryViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: ConnectionService, state: AppState, actions: ActionService,
                 interactions: InteractionService, open_radio_page: Callable[[], None] = lambda: None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._actions = actions
        self._interactions = interactions
        self._open_radio_page = open_radio_page
        self._visible = False
        self._position = 1
        self._cause = ""
        self._detected_by = ""
        self._busy = False
        self._reconnected = False
        self._status_text = ""
        self._status_level = "info"
        state.disconnected.connect(self._on_disconnected)

    visible = qprop(bool, "_visible", changed)
    position = qprop(int, "_position", changed)
    cause = qprop(str, "_cause", changed)
    detectedBy = qprop(str, "_detected_by", changed)
    busy = qprop(bool, "_busy", changed)
    reconnected = qprop(bool, "_reconnected", changed)
    statusText = qprop(str, "_status_text", changed)
    statusLevel = qprop(str, "_status_level", changed)

    @pyqtProperty(bool, notify=changed)
    def wifiAvailable(self) -> bool:  # noqa: N802
        """Req 3/23: Load WiFi PHY only for Everest-family chips."""
        chip = self._state.chip
        return chip is not None and chip.family.upper() == WIFI_FAMILY

    def _on_disconnected(self, position: int, cause: str, detected_by: str) -> None:
        if self._visible:  # one dialog at a time (req §3 debounce)
            return
        self._update(visible=True, position=position, cause=cause, detected_by=detected_by, busy=False,
                     reconnected=False, status_text="", status_level="info")

    @pyqtSlot()
    def reconnect(self) -> None:
        self._update(busy=True, status_text="Reconnecting…", status_level="info")
        self._service.reconnect(self._position).then(
            lambda _: self._update(busy=False, reconnected=True, status_text="Connected. Load a PHY if you need one.",
                                   status_level="ok"),
            lambda e: self._update(busy=False, status_text=f"Reconnect failed: {e.message}", status_level="danger"))

    @pyqtSlot()
    def loadLpwPhy(self) -> None:  # noqa: N802
        """Opens the Radio and PHY page, where the PHY is chosen and loaded (req 23)."""
        self._update(visible=False)
        self._open_radio_page()

    @pyqtSlot()
    def loadWifiPhy(self) -> None:  # noqa: N802
        self._update(visible=False)
        self._open_radio_page()

    @pyqtSlot()
    def addReconnectToActions(self) -> None:  # noqa: N802
        """Req 3: the reconnect operation can be added to Actions for automated recovery."""
        action = self._actions.add("reconnect_rpc", [{"type": "dut_reconnect", "description": "Reconnect RPC"}])
        self._interactions.toast("success", f"Added {action.name} to Actions")

    @pyqtSlot()
    def dismiss(self) -> None:
        self._update(visible=False)
