"""ConnectionService: connect/disconnect/reconnect, PHY loading, and status/disconnect events (req §3)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.models import ConnectResult, DutDisconnected, LoadPhyResult, LpwPhy, PhySpec, StatusChanged
from sirat_ui.gateway.port import StationGateway
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.domains.logs.service import LogService
from sirat_ui.state.app_state import AppState


class ConnectionService:
    def __init__(self, gateway: StationGateway, state: AppState, catalog: RegisterCatalog,
                 errors: ErrorPresenter, log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._catalog = catalog
        self._errors = errors
        self._log = log
        self._last_config: Dict[int, Tuple[str, str, Optional[str], Optional[int]]] = {}
        gateway.events.connect(self._on_event)

    def start(self) -> Call:
        """sys.hello + subscribe + status, as the client does on (re)connect to the service."""
        self._gateway.hello().then(self._on_hello)
        self._gateway.subscribe(["status", "activity", "watch", "instrument", "log"])
        return self.refresh_status()

    def _on_hello(self, hello: dict) -> None:
        self._state.release_id = hello.get("release_id", self._state.release_id)
        self._state.protocol = hello.get("protocol")
        self._state.changed.emit()

    def refresh_status(self) -> Call:
        return self._gateway.status().then(self._state.apply_status)

    def connect(self, position: int, config_type: str = "EFR32", config_file: str = "",
                rpc_host: Optional[str] = None, rpc_port: Optional[int] = None) -> Call:
        """rpc_host/rpc_port override the workspace config for this connection only; None uses it."""
        out: Call = Call()
        self._state.set_connecting(True)
        where = f" at {rpc_host}:{rpc_port}" if rpc_host else ""
        self._log.info(f"Connecting to DUT {position} ({config_type}){where}…")

        def connected(result: ConnectResult) -> None:
            self._last_config[position] = (config_type, config_file, rpc_host, rpc_port)
            self._state.set_chip(position, result.chip)
            self._log.success(f"Connected to DUT {position} · {result.chip.part} rev{result.chip.revision}")
            self.refresh_status()
            self._catalog.load(position).then(lambda _: finish(result), failed)

        def finish(result: ConnectResult) -> None:
            self._log.info(f"Peripheral tree loaded · {len(self._catalog.peripherals)} peripherals")
            self._state.set_connecting(False)
            out.resolve(result)

        def failed(error: ApiError) -> None:
            self._state.set_connecting(False)
            self._errors.present(error, f"Connect DUT {position}")
            out.reject(error)

        self._gateway.connect_dut(position, config_type, config_file, rpc_host, rpc_port).then(connected, failed)
        return out

    def reconnect(self, position: int) -> Call:
        """Same settings as the last successful connect, including an address override (req 3 recovery)."""
        config_type, config_file, host, port = self._last_config.get(position, ("EFR32", "", None, None))
        return self.connect(position, config_type, config_file, host, port)

    def disconnect(self, position: int) -> Call:
        def done(_: object) -> None:
            self._state.set_chip(position, None)
            self._catalog.clear()
            self.refresh_status()

        return self._gateway.disconnect_dut(position).then(done, lambda e: self._errors.present(e, "Disconnect"))

    def load_phy(self, position: int, phy: PhySpec) -> Call[LoadPhyResult]:
        label = phy.name if isinstance(phy, LpwPhy) else phy.config.phy_name
        return self._gateway.load_phy(position, phy).then(
            lambda result: self._log.success(f"PHY {result.name} loaded on DUT {position}"),
            lambda e: self._errors.present(e, f"Load PHY {label}"),
        )

    def _on_event(self, event: object) -> None:
        if isinstance(event, StatusChanged):
            self._state.apply_status(event.status)
        elif isinstance(event, DutDisconnected):
            self._log.error(f"DUT {event.position} disconnect detected ({event.cause})")
            self._state.mark_disconnected(event.position, event.cause, event.detected_by)
