"""Named fake-backend scenarios, so anyone can click through a situation without hardware.

    uv run sirat --scenario flaky_dut
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from sirat_ui.gateway.fake.fake_station import FakeStationGateway
from sirat_ui.models.registers import ChipInfo

_NORMAL_LATENCY = {
    "dut.connect": 700,
    "dut.load_phy": 900,
    "registers.read": 40,
    "registers.read_many": 250,
    "registers.write": 60,
    "registers.write_field": 60,
}


@dataclass
class Scenario:
    name: str
    description: str
    latency: Dict[str, int] = field(default_factory=dict)
    autoconnect: bool = True
    drop_after_reads: int = 0
    chip: Optional[ChipInfo] = None  # another chip family, e.g. Everest for WiFi PHYs


SCENARIOS: Dict[str, Scenario] = {
    s.name: s for s in (
        Scenario("happy", "Connected DUT, normal latency", _NORMAL_LATENCY),
        Scenario("slow_rpc", "Every call is about 10x slower", {k: v * 10 for k, v in _NORMAL_LATENCY.items()}),
        Scenario("flaky_dut", "The DUT drops after a few reads", _NORMAL_LATENCY, drop_after_reads=6),
        Scenario("disconnected_at_start", "Starts with no DUT connected", _NORMAL_LATENCY, autoconnect=False),
        Scenario("everest", "An Everest-family (WiFi) DUT, so WiFi PHYs can be loaded", _NORMAL_LATENCY,
                 chip=ChipInfo("SIWG917M", "B0", "EVEREST")),
    )
}


def apply_scenario(fake: FakeStationGateway, name: str) -> Scenario:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{name}'. Choose one of: {', '.join(SCENARIOS)}")
    scenario = SCENARIOS[name]
    for method, ms in scenario.latency.items():
        fake.set_latency(method, ms)
    fake.drop_after_reads = scenario.drop_after_reads or None
    if scenario.chip:
        fake.chip = scenario.chip
    return scenario
