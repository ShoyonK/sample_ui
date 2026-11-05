"""The parts of a page that open in their own window: the tools the requirements give their own window.

Right-clicking a page in the nav rail lists the page and its parts. A part is a pop-out window kind: the watch
list and the data logger have their own kinds; every other part is a "tool" window that loads its QML file.
Sizes are the requirements' window sizes. `source` is relative to qml/shell/, like the page table's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Tool:
    key: str
    title: str
    page: str
    source: str = ""
    width: int = 900
    height: int = 700
    kind: str = "tool"    # watchList and logger keep the window kinds they had before tools existed
    fill: bool = False    # fills its window (the Advanced tools); a card keeps its own height


TOOLS: List[Tool] = [
    Tool("watchList", "Watch list", "watch", kind="watchList"),
    Tool("logger", "Data logger", "watch", kind="logger"),
    Tool("pyConsole", "Python console", "advanced", "../pages/advanced/ConsoleTool.qml", 900, 700, fill=True),
    Tool("customFunctions", "Custom functions", "advanced", "../pages/advanced/FunctionsTool.qml", 900, 700,
         fill=True),
    Tool("dutControl", "DUT control API explorer", "advanced", "../pages/advanced/DutControlTool.qml", 1200, 800,
         fill=True),
    Tool("memory", "Memory viewer", "advanced", "../pages/advanced/MemoryTool.qml", 800, 600, fill=True),
    Tool("siggen", "Signal generator", "instruments", "../pages/instruments/SiggenCard.qml", 640, 560),
    Tool("blePacket", "BLE packet", "instruments", "../pages/instruments/BlePacketCard.qml", 700, 600),
    Tool("gfsk", "GFSK packet", "instruments", "../pages/instruments/GfskCard.qml", 800, 700),
    Tool("rfSwitch", "RF switch", "instruments", "../pages/instruments/RfSwitchCard.qml", 600, 400),
    Tool("chamber", "Temperature chamber", "instruments", "../pages/instruments/ChamberCard.qml", 560, 520),
    Tool("eca", "ECA capture", "instruments", "../pages/instruments/EcaCard.qml", 1000, 700),
    Tool("prs", "PRS signal routing", "radio", "../pages/radio/PrsCard.qml", 800, 600),
    Tool("wifiPhy", "WiFi PHY configuration", "radio", "../pages/radio/WifiPhyCard.qml", 1100, 800),
    Tool("hardwareConfig", "Hardware configuration", "settings", "../pages/settings/HardwareConfigCard.qml", 600, 520),
    Tool("systemInfo", "System information", "settings", "../pages/settings/SystemInfoCard.qml", 700, 600),
]


def tool(key: str) -> Optional[Tool]:
    return next((t for t in TOOLS if t.key == key and t.kind == "tool"), None)


def page_parts(page: str) -> List[Dict[str, Any]]:
    """The nav rail menu's entries for a page's parts: window kind, arg and key, and the title."""
    parts = []
    for t in TOOLS:
        if t.page == page:
            arg = t.key if t.kind == "tool" else ""
            parts.append({"kind": t.kind, "arg": arg, "key": f"tool:{t.key}" if t.kind == "tool" else t.kind,
                          "title": t.title})
    return parts
