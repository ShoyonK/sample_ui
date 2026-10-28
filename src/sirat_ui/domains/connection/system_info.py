"""System information (req 31): chip, device, RPC and firmware details from dut.info."""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Tuple

from sirat_ui.gateway.models import DutInfo

Section = Tuple[str, List[Tuple[str, str]]]


def _get(d: Dict, key: str, suffix: str = "") -> str:
    value = d.get(key)
    return "—" if value in (None, "") else f"{value}{suffix}"


def sections(info: DutInfo) -> List[Section]:
    """The four req 31 categories, in order. Firmware is shown only if the DUT provides metadata."""
    hw, rta, app = info.hw, info.rta, info.app
    uid = hw.get("UNIQUE_ID")
    result: List[Section] = [
        ("Chip Information", [
            ("Part Number", _get(hw, "PART_NUMBER")),
            ("Chip Revision", _get(hw, "CHIPREVHW_CHIP_REV")),
            ("Family", _get(hw, "CHIPREVHW_FAMILY_NAME")),
            ("Product Revision", _get(hw, "CHIPREVHW_PRODUCT_REV")),
        ]),
        ("Device Information", [
            ("Device Name", _get(hw, "DEVINFO_NAME")),
            ("Flash Size", _get(hw, "MEMINFO_FLASHSIZE", " KB")),
            ("RAM Size", _get(hw, "MEMINFO_RAMSIZE", " KB")),
            ("Unique ID", f"0x{int(uid):016X}" if uid is not None else "—"),
        ]),
        ("RPC Information", [
            ("Host", _get(rta, "host")),
            ("Port", _get(rta, "port")),
            ("Timeout", _get(rta, "timeout_s", " seconds")),
        ]),
    ]
    if app:
        result.append(("Firmware/Application", [
            ("App Name", _get(app, "name")), ("Version", _get(app, "version")),
            ("Build Time", _get(app, "build_time")),
        ]))
    else:
        result.append(("Firmware/Application", [("Status", "The DUT doesn't provide application metadata")]))
    return result


def copy_text(info: DutInfo, now: Optional[dt.datetime] = None) -> str:
    """Req 31 "Copy All" format."""
    lines = ["=== SiRAT System Information ===",
             f"Generated: {(now or dt.datetime.now()):%Y-%m-%d %H:%M:%S}"]
    for title, rows in sections(info):
        lines.append(f"--- {title} ---")
        lines.extend(f"{key}: {value}" for key, value in rows)
    return "\n".join(lines) + "\n"
