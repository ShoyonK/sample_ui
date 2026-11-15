"""Client mirror of the service's check_requires (docs/STATION_API.md "Requires").

The GUI enables buttons from the same table the service enforces: each protocol method's `requires`
(station_protocol), so a stale GUI is still safe.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from station_protocol.catalog import METHODS
from sirat_ui.models.facts import InstrumentFacts, PositionFacts


INSTRUMENT = "instrument:"              # tag prefix: instrument:<kind>

# method -> the state it requires; methods that need nothing have ()
METHOD_REQUIRES: Dict[str, Tuple[str, ...]] = {m.wire: m.requires for m in METHODS}

TAG_TEXT = {
    "dut": "a connected DUT",
    "phy": "a loaded PHY",
    "idle": "the DUT or instrument to be idle",
    "no_fault": "the fault to be cleared (Recover, next to the status in the top bar)",
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
    """Unmet tags in words, for "That needs ... first." ("a connected DUT, the DUT or instrument to be idle")."""
    return ", ".join(TAG_TEXT.get(t, t) for t in tags)
