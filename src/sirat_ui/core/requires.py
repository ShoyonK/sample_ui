"""Client mirror of the service's check_requires (API doc: "State: facts and requires").

The GUI enables buttons from the same table the service enforces, so a stale GUI is still safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class PositionFacts:
    position: int
    dut_connected: bool = False
    phy: Optional[str] = None
    rx_configured: bool = False
    tx_configured: bool = False
    watching: bool = False
    activity: str = "idle"
    fault: Optional[str] = None


METHOD_REQUIRES: Dict[str, Tuple[str, ...]] = {
    "dut.connect": ("no_fault",),
    "dut.info": ("dut",),
    "dut.load_phy": ("dut", "idle"),
    "dut.reset": ("dut", "idle"),
    "rf.prs_route": ("dut",),
    "rf.prs_signals": ("dut",),
    "registers.tree": ("dut",),
    "registers.read": ("dut",),
    "registers.read_many": ("dut",),
    "registers.write": ("dut", "idle"),
    "registers.write_field": ("dut", "idle"),
    "registers.watch": ("dut",),
    "radio.configure_rx": ("dut", "phy", "idle"),
    "radio.configure_tx": ("dut", "phy", "idle"),
    "radio.start_rx": ("dut", "phy", "radio_rx", "idle", "no_fault"),
    "radio.start_tx": ("dut", "phy", "radio_tx", "idle", "no_fault"),
    "automation.seq.run": ("dut", "idle", "no_fault"),
    "advanced.py_exec": ("dut",),
    "advanced.dut_control_invoke": ("dut", "idle"),
    "advanced.custom_function": ("dut", "idle"),
}

TAG_TEXT = {
    "dut": "a connected DUT",
    "phy": "a loaded PHY",
    "radio_rx": "RX to be configured",
    "radio_tx": "TX to be configured",
    "idle": "the DUT to be idle",
    "no_fault": "the fault to be cleared",
}


def _tag_met(tag: str, facts: PositionFacts) -> bool:
    if tag == "dut":
        return facts.dut_connected
    if tag == "phy":
        return facts.phy is not None
    if tag == "radio_rx":
        return facts.rx_configured
    if tag == "radio_tx":
        return facts.tx_configured
    if tag == "idle":
        return facts.activity == "idle"
    if tag == "no_fault":
        return facts.fault is None
    return True


def check_requires(method: str, facts: Optional[PositionFacts]) -> List[str]:
    """Returns the unmet tags for a method; an empty list means the call is allowed."""
    facts = facts or PositionFacts(position=0)
    return [tag for tag in METHOD_REQUIRES.get(method, ()) if not _tag_met(tag, facts)]


def describe_missing(tags: List[str]) -> str:
    return ", ".join(TAG_TEXT.get(t, t) for t in tags)
