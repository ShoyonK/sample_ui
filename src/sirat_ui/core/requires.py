"""Client mirror of the service's check_requires (docs/API_DESIGN.md section 4, "State: facts and requires").

The GUI enables buttons from the same table the service enforces, so a stale GUI is still safe.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from sirat_ui.models.facts import InstrumentFacts, PositionFacts


INSTRUMENT = "instrument:"              # tag prefix: instrument:<kind>

METHOD_REQUIRES: Dict[str, Tuple[str, ...]] = {
    "dut.connect": ("no_fault",),
    "dut.reconnect": ("no_fault",),
    "dut.info": ("dut",),
    "dut.load_phy": ("dut", "idle"),
    "registers.tree": ("dut",),
    "registers.read": ("dut",),
    "registers.read_many": ("dut",),
    "registers.write": ("dut", "idle"),
    "registers.write_field": ("dut", "idle"),
    "registers.watch": ("dut",),
    "memory.read": ("dut",),
    "memory.write": ("dut", "idle"),
    "rf.paths": ("instrument:rf_switch",),
    "rf.connect": ("instrument:rf_switch",),
    "rf.disconnect": ("instrument:rf_switch",),
    "rf.prs_route": ("dut",),
    "rf.prs_signals": ("dut",),
    "instruments.siggen.get": ("instrument:signal_generator",),
    "instruments.siggen.set": ("instrument:signal_generator", "idle"),
    "instruments.siggen.waveforms": ("instrument:signal_generator",),
    "instruments.siggen.trigger": ("instrument:signal_generator",),
    "instruments.siggen.rf": ("instrument:signal_generator",),
    "instruments.chamber.read": ("instrument:chamber",),
    "instruments.chamber.set_temp": ("instrument:chamber", "idle"),
    "instruments.chamber.wait_stable": ("instrument:chamber", "idle"),
    "instruments.eca.sources": ("instrument:eca",),
    "instruments.eca.capture": ("instrument:eca", "idle"),
    "automation.seq.run": ("dut", "idle", "no_fault"),
    "advanced.console.open": ("dut",),
    "advanced.console.exec": ("dut",),
    "advanced.custom_function": ("dut", "idle"),
    "advanced.dut_control.describe": ("dut",),
    "advanced.dut_control.invoke": ("dut", "idle"),
}

TAG_TEXT = {
    "dut": "a connected DUT",
    "phy": "a loaded PHY",
    "idle": "the DUT or instrument to be idle",
    "no_fault": "the fault to be cleared",
    "instrument:signal_generator": "a connected signal generator",
    "instrument:rf_switch": "a connected RF switch",
    "instrument:chamber": "a connected temperature chamber",
    "instrument:eca": "a connected ECA",
}


def _addressed(method: str, instruments: List[InstrumentFacts], instrument_id: Optional[str]) -> List[InstrumentFacts]:
    """The instruments a call talks to: the one with that id, else every instrument of the method's kind."""
    kinds = [t[len(INSTRUMENT):] for t in METHOD_REQUIRES.get(method, ()) if t.startswith(INSTRUMENT)]
    return [i for i in instruments if i.kind in kinds and (instrument_id is None or i.id == instrument_id)]


def _tag_met(tag: str, method: str, facts: PositionFacts, instruments: List[InstrumentFacts],
             instrument_id: Optional[str]) -> bool:
    if tag == "dut":
        return facts.dut_connected
    if tag == "phy":
        return facts.phy is not None
    if tag == "idle":
        if method.startswith("instruments."):  # the addressed instrument's activity, not the position's
            return any(i.connected and i.activity == "idle" for i in _addressed(method, instruments, instrument_id))
        return facts.activity == "idle"
    if tag == "no_fault":
        return facts.fault is None
    if tag.startswith(INSTRUMENT):
        kind = tag[len(INSTRUMENT):]
        return any(i.kind == kind and i.connected and (instrument_id is None or i.id == instrument_id)
                   for i in instruments)
    return True


def check_requires(method: str, facts: Optional[PositionFacts], instruments: Iterable[InstrumentFacts] = (),
                   instrument_id: Optional[str] = None) -> List[str]:
    """Returns the unmet tags for a method; an empty list means the call is allowed. instrument_id: the
    instrument a call with an `id` addresses (API doc section 4, `instrument:<kind>`)."""
    facts = facts or PositionFacts(position=0)
    known = list(instruments)
    return [tag for tag in METHOD_REQUIRES.get(method, ())
            if not _tag_met(tag, method, facts, known, instrument_id)]


def describe_missing(tags: List[str]) -> str:
    return ", ".join(TAG_TEXT.get(t, t) for t in tags)
