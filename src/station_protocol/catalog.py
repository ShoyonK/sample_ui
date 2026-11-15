"""Every method and event of the Station API, collected from the group modules.

A new group is one more module with its METHODS (and its Events), added to the lists below; nothing else
changes. scripts/api/build.py writes the reference and JSON Schema from this catalog.
"""

from __future__ import annotations

from typing import Dict, Tuple

from station_protocol import (activity, advanced, automation, dut, instruments, log, memory, registers, rf, system,
                              tests)
from station_protocol.method import Event, Method

GROUPS = (system, dut, rf, registers, activity, automation, tests, instruments, memory, advanced)

METHODS: Tuple[Method, ...] = tuple(m for group in GROUPS for m in group.METHODS)
BY_WIRE: Dict[str, Method] = {m.wire: m for m in METHODS}

EVENTS: Tuple[Event, ...] = (system.STATUS_CHANGED, dut.DUT_DISCONNECTED, registers.WATCH, activity.PROGRESS,
                             activity.FINISHED, log.LOG_LINE, system.CALL_LATE)
BY_EVENT: Dict[str, Event] = {e.name: e for e in EVENTS}

# sys.subscribe topics; each event above names the one that brings it
TOPICS: Tuple[str, ...] = ("status", "activity", "watch", "log")

assert len(BY_WIRE) == len(METHODS), "two methods share a wire name"
assert {e.topic for e in EVENTS if e.topic} == set(TOPICS), "an event's topic isn't in TOPICS"
