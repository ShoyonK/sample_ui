"""Hardware configuration (req 32): RPC host/port/timeout and DUT position, in ~/.sirat/hardware_config.json.

With the Station API the service owns the DUT connection and normally takes the DUT's RPC address
from the workspace config. When rpc_override is on, host and port are sent with dut.connect to
override it for that connection (docs/API_CHANGE_dut_connect_rpc_address.md). The timeout is applied
through dut.set_rpc_timeout. Extra keys don't bother the old GUI, which reads the four it knows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from sirat_ui.core.observable import Event
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.port import StationGateway
from sirat_ui.state.app_state import AppState
from sirat_ui.stores.json_store import JsonStore


@dataclass
class HardwareConfig:
    rpc_host: str = "localhost"
    rpc_port: int = 10001
    rpc_timeout: int = 5
    dut_position: int = 1
    rpc_override: bool = False  # off: the station's workspace config decides the address

    @property
    def address(self) -> Tuple[Optional[str], Optional[int]]:
        """What to send with dut.connect: (None, None) means "use the workspace config"."""
        return (self.rpc_host, self.rpc_port) if self.rpc_override else (None, None)

    @classmethod
    def from_json(cls, raw: Any) -> "HardwareConfig":
        config = cls()
        if isinstance(raw, dict):
            config.rpc_host = str(raw.get("rpc_host", config.rpc_host))
            config.rpc_override = bool(raw.get("rpc_override", False))
            for key in ("rpc_port", "rpc_timeout", "dut_position"):
                try:
                    setattr(config, key, int(raw.get(key, getattr(config, key))))
                except (TypeError, ValueError):
                    pass
        return config

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


def validate(host: str, port: str, timeout: str, position: str, override: bool = True) -> Dict[str, str]:
    """Req 32 input validation. Returns {field: message} for every invalid field.
    Host and port only matter (and are only checked) when the address override is on."""
    errors: Dict[str, str] = {}
    if override and not host.strip():
        errors["host"] = "Enter a host name or IP address"

    def int_in(value: str, lo: int, hi: int, key: str, label: str) -> None:
        try:
            number = int(value)
        except ValueError:
            errors[key] = f"{label} must be a whole number"
            return
        if not lo <= number <= hi:
            errors[key] = f"{label} must be between {lo} and {hi}"

    if override:
        int_in(port, 1, 65535, "port", "Port")
    int_in(timeout, 1, 300, "timeout", "Timeout")
    int_in(position, 1, 4, "position", "Position")
    return errors


class HardwareConfigService:
    def __init__(self, store: JsonStore, gateway: StationGateway, state: AppState, log: LogService) -> None:
        self._store = store
        self._gateway = gateway
        self._state = state
        self._log = log
        self.config = HardwareConfig.from_json(store.load())
        self.config_changed = Event()

    def reload(self) -> None:
        self.config = HardwareConfig.from_json(self._store.load())
        self.config_changed.emit()

    def save(self, config: HardwareConfig) -> Call:
        """Writes the file, applies the timeout to the station and selects the DUT position."""
        self.config = config
        self._store.save(config.to_json())
        self._state.set_position(config.dut_position)
        where = f"{config.rpc_host}:{config.rpc_port}" if config.rpc_override else "workspace config address"
        self._log.info(f"Hardware configuration saved ({where}, {config.rpc_timeout} s, DUT {config.dut_position})")
        self.config_changed.emit()
        return self._gateway.set_rpc_timeout(config.rpc_timeout)

    def test_connection(self, config: HardwareConfig) -> Call:
        """Req 32: try the connection without keeping it. Resolves to a message, rejects with ApiError."""
        pos = config.dut_position
        out: Call = Call()
        already_connected = self._state.facts.dut_connected and self._state.position == pos

        def probe(_=None) -> None:
            self._gateway.dut_info(pos).then(lambda info: finish(info), out.reject)

        def finish(info) -> None:
            address = f"{info.rta.get('host')}:{info.rta.get('port')}"
            message = f"Connection successful! {info.chip} rev{info.revision} at DUT {pos} ({address})"
            if already_connected:
                message += ", using the existing connection"
            if already_connected:
                out.resolve(message)
            else:  # a test must not leave a connection behind
                self._gateway.disconnect_dut(pos).then(lambda _: out.resolve(message), lambda _: out.resolve(message))

        def timeout_set(_=None) -> None:
            if already_connected:
                probe()
            else:
                host, port = config.address
                self._gateway.connect_dut(pos, "EFR32", "", host, port).then(probe, out.reject)

        self._gateway.set_rpc_timeout(config.rpc_timeout).then(timeout_set, out.reject)
        return out
