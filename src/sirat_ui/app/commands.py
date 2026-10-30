"""The Ctrl+K command list (req 2 palette). Page commands navigate first, then open the tool."""

from __future__ import annotations

from typing import Callable, List

from sirat_ui.domains.advanced.advanced_viewmodel import AdvancedViewModel
from sirat_ui.domains.automation.actions_viewmodel import ActionsViewModel
from sirat_ui.domains.connection.viewmodels import ConnectionViewModel
from sirat_ui.domains.dumps.viewmodel import DumpsViewModel
from sirat_ui.domains.monitoring.watch_viewmodel import WatchListViewModel
from sirat_ui.domains.registers.detail_viewmodel import RegisterDetailViewModel
from sirat_ui.domains.registers.tree_viewmodels import PeripheralTreeViewModel
from sirat_ui.domains.sessions.viewmodel import SessionsViewModel
from sirat_ui.domains.shell.command_palette import Command
from sirat_ui.domains.shell.dock import DockViewModel
from sirat_ui.domains.shell.viewmodels import StateViewModel

Go = Callable[..., Callable[[], None]]   # go(page, then=...) -> a command that navigates, then runs `then`


def palette_commands(go: Go, connection: ConnectionViewModel, state: StateViewModel, detail: RegisterDetailViewModel,
                     tree: PeripheralTreeViewModel, actions: ActionsViewModel, watch: WatchListViewModel,
                     dock: DockViewModel, dumps: DumpsViewModel, advanced: AdvancedViewModel,
                     sessions: SessionsViewModel) -> List[Command]:
    def tool(name: str) -> Callable[[], None]:
        return go("advanced", lambda: advanced.show(name))

    return [
        Command("connect", "Connect to DUT…", "Open the connection sheet", connection.openSheet),
        Command("dark", "Toggle dark mode", "Switch between light and dark", state.toggleDarkMode),
        Command("read", "Read the selected register", "Same as the Read button", detail.read, "F5"),
        Command("run_checked", "Run checked actions", "Same as Run checked", actions.runSelected, "Ctrl+R"),
        Command("toggle_live", "Start or pause the watch list", "Live refresh on the Watch page",
                go("watch", watch.toggleLive), "Ctrl+L"),
        Command("toggle_dock", "Show or hide History, Actions and Log", "The panels under every page", dock.toggle,
                "Ctrl+J"),
        Command("take_dump", "Take a dump…", "Read selected peripherals and save them as a CSV",
                go("dumps", dumps.openPicker)),
        Command("radio_diff", "Radio Calculator diff…", "Compare the chip with a Radio Calculator .cfg",
                go("dumps", dumps.openRadioDiff)),
        Command("load_phy", "Load LPW PHY…", "Load a BLE or 802.15.4 PHY", go("radio")),
        Command("wifi_phy", "Load WiFi PHY…", "Configure and load a WiFi PHY (Everest family)", go("radio")),
        Command("prs", "PRS signal routing", "Route an internal signal to a GPIO pin", go("radio")),
        Command("siggen", "Signal generator", "Configure, trigger and switch RF on the signal generator",
                go("instruments")),
        Command("rf_switch", "RF switch", "Connect a switch path to a DUT position", go("instruments")),
        Command("chamber", "Temperature chamber", "Set and watch the chamber temperature", go("instruments")),
        Command("eca", "ECA capture", "Capture, plot and measure radio timing signals", go("instruments")),
        Command("ble_packet", "BLE packet code", "Generate BLE or GFSK packet code", go("instruments")),
        Command("py_console", "Python console", "Run Python on the station with dut available", tool("Console")),
        Command("custom_functions", "Custom functions", "Write, run and save Python functions",
                tool("Custom functions")),
        Command("dut_control", "DUT control API explorer", "Browse and call dut.dut_control methods",
                tool("DUT control")),
        Command("memory", "Memory viewer", "Read and write raw memory at an address", tool("Memory")),
        Command("save_session", "Save session…", "Save notes, formulas, actions, favorites and history",
                sessions.saveSession, "Ctrl+S"),
        Command("load_session", "Load session…", "Browse saved sessions", sessions.openBrowser),
        Command("tree_search", "Filter the register tree", "Focus the tree's filter box",
                go("registers", tree.requestSearchFocus), "Ctrl+F"),
    ]
