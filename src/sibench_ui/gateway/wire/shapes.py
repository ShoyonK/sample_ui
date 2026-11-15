"""The register tree: the protocol's RegisterTree <-> the app's register models.

Most results travel as the models' own fields. The register tree doesn't: the protocol's RegisterTree
(station_protocol/registers.py) puts `critical` and `read_sensitive` on the peripheral, has `reset_value` (null
when the SVD gives none), and leaves out the back-references the app's models carry (each register's
`peripheral`, each field's `register`).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from station_protocol.registers import RegisterTree
from sibench_ui.models.registers import AccessType, EnumValue, FieldDef, PeripheralDef, RegisterDef


def tree_to_wire(peripherals: List[PeripheralDef]) -> Dict[str, Any]:
    """The app's register models as the contract's RegisterTree. A peripheral is critical (or read-sensitive)
    when any of its registers is; the station describes it per peripheral, so they always agree."""
    out = [{
        "name": p.name, "base_address": p.base_address, "description": p.description,
        "critical": any(r.critical for r in p.registers),
        "read_sensitive": any(r.read_sensitive for r in p.registers),
        "registers": [{
            "name": r.name, "address": r.address, "width": r.width, "access": r.access.value,
            "reset_value": r.reset, "description": r.description,
            "fields": [{"name": f.name, "lsb": f.lsb, "width": f.width, "access": f.access.value,
                        "description": f.description,
                        "enums": [{"name": e.name, "value": e.value, "description": e.description} for e in f.enums]}
                       for f in r.fields],
        } for r in p.registers],
    } for p in peripherals]
    digest = hashlib.sha256(json.dumps(out, sort_keys=True).encode("utf-8")).hexdigest()
    return {"tree_id": f"sha256:{digest[:16]}", "peripherals": out}


def tree_from_wire(tree: RegisterTree) -> List[PeripheralDef]:
    """A validated RegisterTree as the app's models, with the back-references filled in."""
    peripherals = []
    for p in tree["peripherals"]:
        registers = []
        for r in p["registers"]:
            full = f"{p['name']}.{r['name']}"
            fields = tuple(FieldDef(full, f["name"], f["lsb"], f["width"], AccessType(f["access"].value),
                                    f["description"],
                                    tuple(EnumValue(e.name, e.value, e.description) for e in f["enums"]))
                           for f in r["fields"])
            registers.append(RegisterDef(p["name"], r["name"], r["address"], AccessType(r["access"].value),
                                         r["width"], r["description"], fields, r["reset_value"] or 0,
                                         p["critical"], p["read_sensitive"]))
        peripherals.append(PeripheralDef(p["name"], p["base_address"], p["description"], tuple(registers)))
    return peripherals
