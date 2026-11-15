"""instruments: the bench's instruments: signal generator, temperature chamber and ECA (the RF switch is rf)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from typing_extensions import Literal

from station_protocol.common import ACTIVITY, ID, Count, InstrumentFacts, Offset
from station_protocol.method import Method, Param

TriggerMode = Literal["infinite", "single"]

SIGGEN = ("instrument:signal_generator",)
CHAMBER = ("instrument:chamber",)
ECA = ("instrument:eca",)


@dataclass
class SiggenConfig:
    """What a signal generator is loaded with. The wire carries Hz; the GUI shows MHz."""
    sg_type: str = "PacketSrw"
    input_config_name: str = ""
    frequency_hz: float = 2440e6
    power_dbm: float = 0.0
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChamberReading:
    """instruments.chamber.read."""
    actual_c: float
    target_c: float
    stable: bool


@dataclass(frozen=True)
class EcaSources:
    """The ECA's channels and trigger sources."""
    channels: Tuple[str, ...]
    triggers: Tuple[str, ...]          # trigger sources; "immediate" is always allowed too


@dataclass(frozen=True)
class CaptureSpec:
    """What an ECA capture records and how it triggers."""
    channels: Tuple[str, ...]
    trigger: str                       # a trigger source, or "immediate"
    edge: str = "rising"
    sample_rate_hz: float = 1e6
    duration_s: float = 0.01
    pretrigger_pct: int = 10


@dataclass(frozen=True)
class CaptureMeta:
    """A finished capture's spec, start time and sample count."""
    spec: CaptureSpec
    started_at: float
    sample_count: int
    chip: str = ""
    pos: int = 0


@dataclass(frozen=True)
class CapturePage:
    """One page of a capture: channel -> base64 little-endian int16 samples for [offset, offset+count)."""
    meta: CaptureMeta
    offset: int
    count: int
    channels: Dict[str, str]
    more: bool


METHODS = (
    Method("instruments.list", (), List[InstrumentFacts], wrap="instruments"),
    Method("instruments.connect", (ID, Param("address", Optional[str], None)), None),
    Method("instruments.siggen.get", (ID,), SiggenConfig, requires=SIGGEN),
    Method("instruments.siggen.set", (ID, Param("config", SiggenConfig)), None, requires=SIGGEN + ("idle",)),
    Method("instruments.siggen.waveforms", (ID, Param("reload", bool, False)), List[str], wrap="names",
           requires=SIGGEN),
    Method("instruments.siggen.trigger", (ID, Param("mode", TriggerMode)), None, requires=SIGGEN),
    Method("instruments.siggen.rf", (ID, Param("on", bool)), None, requires=SIGGEN),
    Method("instruments.chamber.read", (ID,), ChamberReading, requires=CHAMBER),
    Method("instruments.chamber.set_temp", (ID, Param("celsius", float)), None, requires=CHAMBER + ("idle",)),
    Method("instruments.chamber.wait_stable", (ID, Param("tolerance_c", float, 0.5), Param("hold_s", float, 60.0),
                                               Param("timeout_s", float, 3600.0)), str, wrap=ACTIVITY,
           requires=CHAMBER + ("idle",)),
    Method("instruments.eca.sources", (ID,), EcaSources, requires=ECA),
    Method("instruments.eca.capture", (ID, Param("spec", CaptureSpec)), str, wrap=ACTIVITY, requires=ECA + ("idle",)),
    Method("instruments.eca.result", (Param("capture_id", str), Param("offset", Offset, 0),
                                      Param("count", Count, 65536)), CapturePage),
)
