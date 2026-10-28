"""Hardware configuration (req 32): RPC host/port/timeout and DUT position, in ~/.sirat/hardware_config.json.

With the Station API the service owns the DUT connection and normally takes the DUT's RPC address
from the workspace config. When rpc_override is on, host and port are sent with dut.connect to
override it for that connection (docs/API_DESIGN.md, dut.connect). The timeout is applied
through dut.set_rpc_timeout. Extra keys don't bother the old GUI, which reads the four it knows.
"""

from __future__ import annotations

from typing import Dict

from sirat_ui.core.observable import Event
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.port import DutPort
from sirat_ui.models.settings import HardwareConfig
from sirat_ui.models.station import ProbeResult
from sirat_ui.state.station import StationState
from sirat_ui.stores.json_store import JsonStore


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
    def __init__(self, store: JsonStore, gateway: DutPort, state: StationState, log: LogService) -> None:
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
        """Req 32: can the DUT's RPC server be reached? dut.probe never connects or drops a connection, so testing
        a position that's in use is safe. Resolves to a message; rejects with ApiError, or with a TIMEOUT-coded
        ApiError carrying the probe's detail when nothing answered."""
        out: Call = Call()

        def probed(result: ProbeResult) -> None:
            if result.ok:
                out.resolve(f"Connection successful! {result.detail} ({result.latency_ms:.0f} ms)")
            else:
                out.reject(ApiError(ErrorCode.TIMEOUT, result.detail))

        self._gateway.probe(config.dut_position, config.rpc, config.rpc_timeout).then(probed, out.reject)
        return out
