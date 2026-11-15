"""ConnectionService: connect/disconnect/reconnect, PHY loading, and status/disconnect events (req §3)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Tuple

from sibench_ui.domains.logs.service import LogService
from sibench_ui.domains.registers.catalog import RegisterCatalog
from sibench_ui.gateway.call import Call
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.port import DutPort, SystemPort
from sibench_ui.models.station import (ConnectResult, DutDisconnected, LoadPhyResult, LpwPhy, PhySpec, RpcAddress,
                                     StatusChanged)
from sibench_ui.shared.error_presenter import ErrorPresenter
from sibench_ui.state.station import StationState


class ConnectionGateway(SystemPort, DutPort, Protocol):
    """Connecting needs the station handshake (sys.*) and the DUT calls (dut.*)."""


class ConnectionService:
    """The station handshake and the DUT connection: connect, reconnect, recover, disconnect, load a PHY, and the
    status and disconnect events that keep StationState current."""

    def __init__(self, gateway: ConnectionGateway, state: StationState, catalog: RegisterCatalog,
                 errors: ErrorPresenter, log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._catalog = catalog
        self._errors = errors
        self._log = log
        self._last_config: Dict[int, Tuple[str, str, Optional[RpcAddress]]] = {}
        gateway.events.connect(self._on_event)

    def start(self) -> Call:
        """sys.hello + subscribe + status, as the client does on (re)connect to the service."""
        self._gateway.hello().then(self._on_hello)
        self._gateway.subscribe(["status", "activity", "watch", "log"])
        return self.refresh_status()

    def _on_hello(self, hello: Dict[str, Any]) -> None:
        self._state.release_id = hello.get("release_id", self._state.release_id)
        self._state.protocol = hello.get("protocol")
        self._state.changed.emit()

    def refresh_status(self) -> Call:
        return self._gateway.status().then(self._state.apply_status)

    def connect(self, position: int, config_type: str = "EFR32", config_file: str = "",
                rpc: Optional[RpcAddress] = None) -> Call:
        """Connects the DUT, then loads its register tree if it's the selected DUT. Resolves once both are done.

        Args:
            position: The DUT position (1-4).
            config_type: EFR32 or EFX.
            config_file: The bench config file, or "" for the station default.
            rpc: Overrides the workspace config's address for this connection only; None uses it.
        """
        out: Call[ConnectResult] = Call()
        self._state.set_connecting(True)
        where = f" at {rpc.host}:{rpc.port}" if rpc else ""
        self._log.info(f"Connecting to DUT {position} ({config_type}){where}…")

        def connected(result: ConnectResult) -> None:
            self._last_config[position] = (config_type, config_file, rpc)
            self._state.set_chip(position, result.chip)
            self._log.success(f"Connected to DUT {position} · {result.chip.part} rev{result.chip.revision}")
            self.refresh_status()
            if position != self._state.position:   # not the DUT on screen: its tree loads when you switch to it
                finish(result, loaded=False)
                return
            self._catalog.load(position).then(lambda _: finish(result), failed)

        def finish(result: ConnectResult, loaded: bool = True) -> None:
            if loaded:
                self._log.info(f"Peripheral tree loaded · {len(self._catalog.peripherals)} peripherals")
            self._state.set_connecting(False)
            out.resolve(result)

        def failed(error: ApiError) -> None:
            self._state.set_connecting(False)
            self._errors.present(error, f"Connect DUT {position}")
            out.reject(error)

        self._gateway.connect_dut(position, config_type, config_file, rpc).then(connected, failed)
        return out

    def reconnect(self, position: int) -> Call:
        """Req 3 recovery: RPC only (dut.reconnect), so the bench setup isn't redone. A position the service has
        never connected falls back to a full connect with the last settings."""
        out: Call[None] = Call()
        self._log.info(f"Reconnecting RPC to DUT {position}…")

        def done(_: None) -> None:
            self.refresh_status()
            out.resolve(None)

        def failed(error: ApiError) -> None:
            if error.code == ErrorCode.NOT_FOUND:
                config_type, config_file, rpc = self._last_config.get(position, ("EFR32", "", None))
                self.connect(position, config_type, config_file, rpc).then(lambda _: out.resolve(None), out.reject)
                return
            self._errors.present(error, f"Reconnect DUT {position}")
            out.reject(error)

        self._gateway.reconnect_dut(position).then(done, failed)
        return out

    def dut_info(self) -> Call:
        """Req 31 system information for the selected position (DutInfo). The caller shows failures inline."""
        return self._gateway.dut_info(self._state.position)

    def recover(self, position: int) -> Call:
        """sys.recover: applies the safe state and clears the position's fault (set by a hardware error during a
        run). Until then the station refuses runs that require no_fault."""
        def done(_: object) -> None:
            self._log.success(f"DUT {position} recovered: safe state applied, fault cleared")

        return self._gateway.recover(position).then(done, lambda e: self._errors.present(e, f"Recover DUT {position}"))

    def disconnect(self, position: int) -> Call:
        """Disconnects the DUT; its chip is cleared, and the register catalog if that DUT is the selected one."""
        def done(_: object) -> None:
            self._state.set_chip(position, None)
            if position == self._state.position:
                self._catalog.clear()
            self.refresh_status()

        return self._gateway.disconnect_dut(position).then(done, lambda e: self._errors.present(e, "Disconnect"))

    def show_position(self, position: int) -> None:
        """You switched to another DUT: the register catalog becomes that DUT's tree (each DUT can be a different
        chip), or empty while nothing is connected there."""
        if not self._state.facts_for(position).dut_connected:
            self._catalog.clear()
            return
        self._catalog.load(position).then(
            None, lambda e: self._errors.present(e, f"Load the register tree of DUT {position}"))

    def load_phy(self, position: int, phy: PhySpec) -> Call[LoadPhyResult]:
        """Loads an LPW or WiFi PHY; success is logged and failure presented."""
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
