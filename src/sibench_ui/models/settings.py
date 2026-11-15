"""User settings: preferences, hardware config, and problems found in a settings file."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, Optional

from sibench_ui.core.formatting import ValueFormat
from sibench_ui.models.station import RpcAddress


@dataclass
class Preferences:
    """~/.sibench/preferences.json."""
    value_format: str = ValueFormat.HEX.value
    auto_read_on_click: bool = True
    show_secure_peripherals: bool = False
    confirm_critical_writes: bool = True
    dark_mode: bool = False
    last_position: int = 1
    watch_density: str = "compact"   # "large": bigger values on the Watch page, readable from the bench

    @property
    def format(self) -> ValueFormat:
        try:
            return ValueFormat(self.value_format)
        except ValueError:
            return ValueFormat.HEX

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: Any) -> "Preferences":
        """Preferences from the file's dict; unknown keys are dropped and anything that isn't a dict gives defaults."""
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class HardwareConfig:
    """~/.sibench/hardware_config.json (req 32)."""
    rpc_host: str = "localhost"
    rpc_port: int = 10001
    rpc_timeout: int = 5
    dut_position: int = 1
    rpc_override: bool = False  # off: the station's workspace config decides the address

    @property
    def rpc(self) -> Optional[RpcAddress]:
        """What to send with dut.connect and dut.probe: None means "use the workspace config"."""
        return RpcAddress(self.rpc_host, self.rpc_port) if self.rpc_override else None

    @classmethod
    def from_json(cls, raw: Any) -> "HardwareConfig":
        """The config from the file's dict; numbers that don't parse keep their defaults."""
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


@dataclass(frozen=True)
class Problem:
    """One entry skipped while loading a settings file."""
    source: str   # file name, e.g. ".sibench/actions.json"
    where: str    # path inside it, e.g. "lpmode_on.operations.0.value"
    message: str

    def __str__(self) -> str:
        return f"{self.source}: {self.where}: {self.message}" if self.where else f"{self.source}: {self.message}"
