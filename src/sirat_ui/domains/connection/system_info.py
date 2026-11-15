"""System information (req 31): chip, device, RPC and firmware details from dut.info."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from sirat_ui.models.station import DutInfo

Section = Tuple[str, List[Tuple[str, str]]]
SECTION_TITLES = ["Chip Information", "Device Information", "RPC Information", "Firmware/Application"]


def _get(d: Dict[str, Any], key: str, suffix: str = "") -> str:
    value = d.get(key)
    return "—" if value in (None, "") else f"{value}{suffix}"


def sections(info: DutInfo) -> List[Section]:
    """The four req 31 categories, in order. Firmware is shown only if the DUT provides metadata."""
    hw, rta, app = info.hw, info.rta, info.app
    uid = hw.get("UNIQUE_ID")
    chip_title, device_title, rpc_title, firmware_title = SECTION_TITLES
    result: List[Section] = [
        (chip_title, [
            ("Part Number", _get(hw, "PART_NUMBER")),
            ("Chip Revision", _get(hw, "CHIPREVHW_CHIP_REV")),
            ("Family", _get(hw, "CHIPREVHW_FAMILY_NAME")),
            ("Product Revision", _get(hw, "CHIPREVHW_PRODUCT_REV")),
        ]),
        (device_title, [
            ("Device Name", _get(hw, "DEVINFO_NAME")),
            ("Flash Size", _get(hw, "MEMINFO_FLASHSIZE", " KB")),
            ("RAM Size", _get(hw, "MEMINFO_RAMSIZE", " KB")),
            ("Unique ID", f"0x{int(uid):016X}" if uid is not None else "—"),
        ]),
        (rpc_title, [
            ("Host", _get(rta, "host")),
            ("Port", _get(rta, "port")),
            ("Timeout", _get(rta, "timeout_s", " seconds")),
        ]),
    ]
    if app:
        result.append((firmware_title, [
            ("App Name", _get(app, "name")), ("Version", _get(app, "version")),
            ("Build Time", _get(app, "build_time")),
        ]))
    else:
        result.append((firmware_title, [("Status", "The DUT doesn't provide application metadata")]))
    return result


def copy_text(info: DutInfo, now: Optional[dt.datetime] = None) -> str:
    """Req 31 "Copy All" format."""
    lines = ["=== SiRAT System Information ===",
             f"Generated: {(now or dt.datetime.now()):%Y-%m-%d %H:%M:%S}"]
    for title, rows in sections(info):
        lines.append(f"--- {title} ---")
        lines.extend(f"{key}: {value}" for key, value in rows)
    return "\n".join(lines) + "\n"
