"""ServiceContainer: the composition root. Builds every service and ViewModel and wires them together.

Nothing else in the app constructs services; tests build a container with a fake gateway and a tmp home.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

from PyQt5.QtCore import QObject

from sirat_ui.domains.annotations.formula_viewmodel import FormulaEditorViewModel
from sirat_ui.domains.annotations.service import AnnotationService, FavoritesService
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.automation.sequences import SequenceService
from sirat_ui.domains.automation.action_editor import ActionEditorViewModel
from sirat_ui.domains.automation.actions_viewmodel import ActionsViewModel
from sirat_ui.domains.automation.sequences_viewmodel import SequencesViewModel
from sirat_ui.domains.connection.service import ConnectionService
from sirat_ui.domains.dumps.service import DumpService
from sirat_ui.domains.radio.phy import PhyService
from sirat_ui.domains.radio.phy_viewmodels import LpwPhyViewModel, WifiPhyViewModel
from sirat_ui.domains.radio.prs import PrsService
from sirat_ui.domains.radio.prs_viewmodel import PrsViewModel
from sirat_ui.domains.dumps.viewmodel import DumpsViewModel
from sirat_ui.domains.connection.viewmodels import ConnectionViewModel, DisconnectRecoveryViewModel
from sirat_ui.domains.history.service import HistoryLog
from sirat_ui.domains.history.viewmodel import HistoryViewModel
from sirat_ui.domains.logs.service import LogService
from sirat_ui.domains.logs.viewmodel import LogViewModel
from sirat_ui.domains.monitoring.logger import DataLoggerService
from sirat_ui.domains.monitoring.watch import WatchService
from sirat_ui.domains.monitoring.logger_viewmodel import DataLoggerViewModel
from sirat_ui.domains.monitoring.watch_viewmodel import WatchListViewModel
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.registers.read_all import ReadAllService
from sirat_ui.domains.registers.read_all_viewmodel import ReadAllViewModel
from sirat_ui.domains.registers.detail_viewmodel import RegisterDetailViewModel
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.domains.registers.tree_viewmodels import FavoritesViewModel, PeripheralTreeViewModel
from sirat_ui.domains.shell.command_palette import Command, CommandPaletteViewModel
from sirat_ui.domains.shell.viewmodels import ShellViewModel, StateViewModel
from sirat_ui.domains.shell.windows import WindowsViewModel
from sirat_ui.domains.settings.hardware import HardwareConfigService
from sirat_ui.domains.settings.transfer import SettingsTransfer
from sirat_ui.domains.settings.viewmodels import HardwareConfigViewModel, SettingsViewModel
from sirat_ui.domains.connection.system_info_viewmodel import SystemInfoViewModel
from sirat_ui.domains.sessions.service import SessionService, count
from sirat_ui.domains.sessions.viewmodel import SessionsViewModel
from sirat_ui.gateway.port import StationGateway
from sirat_ui.gateway.scheduler import Scheduler
from sirat_ui.shared.dialogs import DialogsViewModel, QmlInteractions
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.state.app_state import AppState
from sirat_ui.state.preferences import Preferences
from sirat_ui.stores.json_store import UserStores


@dataclass
class Services:
    log: LogService
    history: HistoryLog
    errors: ErrorPresenter
    catalog: RegisterCatalog
    registers: RegisterService
    read_all: ReadAllService
    connection: ConnectionService
    favorites: FavoritesService
    annotations: AnnotationService
    watch: WatchService
    logger: DataLoggerService
    actions: ActionService
    sequences: SequenceService
    hardware: HardwareConfigService
    transfer: SettingsTransfer
    dumps: DumpService
    phy: PhyService
    prs: PrsService
    sessions: SessionService


class ServiceContainer:
    def __init__(self, gateway: StationGateway, home: Path, scheduler: Scheduler, backend_label: str = "",
                 interactions: Optional[InteractionService] = None, dumps_dir: Optional[Path] = None) -> None:
        self.gateway = gateway
        self.scheduler = scheduler
        self.home = Path(home)
        self.dumps_dir = Path(dumps_dir) if dumps_dir else self.home / ".sirat" / "dumps"
        self.stores = UserStores.in_home(self.home)
        self.state = AppState(Preferences.from_json(self.stores.preferences.load()), backend_label)
        self.state.preferences_changed.connect(lambda prefs: self.stores.preferences.save(prefs.to_json()))

        self.dialogs = DialogsViewModel(is_dark=lambda: self.state.preferences.dark_mode)
        self.interactions: InteractionService = interactions or QmlInteractions(self.dialogs)
        self.services = self._build_services()
        self.shell = self._build_viewmodels()

    def _build_services(self) -> Services:
        log = LogService()
        self.gateway.events.connect(log.on_gateway_event)
        history = HistoryLog()
        errors = ErrorPresenter(self.interactions, log)
        catalog = RegisterCatalog(self.gateway, self.state)
        registers = RegisterService(self.gateway, self.state, history, self.interactions, errors, log)
        read_all = ReadAllService(registers, self.interactions, log)
        connection = ConnectionService(self.gateway, self.state, catalog, errors, log)
        favorites = FavoritesService(self.stores.favorites)
        annotations = AnnotationService(self.stores.notes, self.stores.formulas)
        watch = WatchService(self.gateway, self.state, catalog, registers, self.stores.watch_list, errors)
        logger = DataLoggerService(self.gateway, self.state, catalog, annotations, self.stores.data_logger, errors,
                                   self.scheduler)
        actions = ActionService(self.stores.actions, self.gateway, self.state, errors, log,
                                self.stores.custom_functions)
        sequences = SequenceService(self.stores.sequences, actions, self.gateway, self.state, errors, log)
        hardware = HardwareConfigService(self.stores.hardware_config, self.gateway, self.state, log)
        transfer = SettingsTransfer(self.stores, self.reload_user_data)
        dumps = DumpService(self.dumps_dir, catalog, registers, log)
        phy = PhyService(connection, self.state, actions)
        prs = PrsService(self.gateway, self.state, history, actions, errors, log)
        sessions = SessionService(self.home / ".sirat" / "sessions", self.home / ".sirat" / "autosave.json",
                                  annotations, favorites, actions, history, dumps, log, self.scheduler)
        return Services(log, history, errors, catalog, registers, read_all, connection, favorites, annotations,
                        watch, logger, actions, sequences, hardware, transfer, dumps, phy, prs, sessions)

    def _build_viewmodels(self) -> ShellViewModel:
        s, st, ix = self.services, self.state, self.interactions
        editor = ActionEditorViewModel(s.actions, s.catalog, st, ix)
        formulas = FormulaEditorViewModel(s.annotations, ix)
        # ViewModels the palette commands call are typed locals, so those calls are checked
        state_vm = StateViewModel(st)
        sessions_vm = SessionsViewModel(s.sessions, ix)
        connection_vm = ConnectionViewModel(s.connection, st, s.log, s.hardware, ix)
        tree_vm = PeripheralTreeViewModel(st, s.catalog, s.registers, s.read_all)
        detail_vm = RegisterDetailViewModel(st, s.registers, s.favorites, s.annotations, s.watch, s.logger,
                                            s.actions, ix, formulas, s.read_all)
        actions_vm = ActionsViewModel(s.actions, s.sequences, editor, st, ix)
        sequences_vm = SequencesViewModel(s.sequences, s.actions, st, ix)
        dumps_vm = DumpsViewModel(s.dumps, s.catalog, st, ix)

        def go(page: str, then: Callable[[], object] = lambda: None) -> Callable[[], None]:
            def run() -> None:
                self.shell.navigate(page)
                then()
            return run

        palette = CommandPaletteViewModel(
            st, s.catalog, s.actions, s.sequences,
            navigate=lambda key: self.shell.navigate(key),
            select_action=actions_vm.select_name,
            select_sequence=sequences_vm.select_name,
            commands=[
                Command("connect", "Connect to DUT…", "Open the connection sheet", connection_vm.openSheet),
                Command("dark", "Toggle dark mode", "Switch between light and dark", state_vm.toggleDarkMode),
                Command("read", "Read the selected register", "Same as the Read button", detail_vm.read),
                Command("run_checked", "Run checked actions", "Same as Run checked", actions_vm.runSelected),
                Command("take_dump", "Take a dump…", "Read selected peripherals and save them as a CSV",
                        go("dumps", dumps_vm.openPicker)),
                Command("radio_diff", "Radio Calculator diff…", "Compare the chip with a Radio Calculator .cfg",
                        go("dumps", dumps_vm.openRadioDiff)),
                Command("load_phy", "Load LPW PHY…", "Load a BLE or 802.15.4 PHY", go("radio")),
                Command("wifi_phy", "Load WiFi PHY…", "Configure and load a WiFi PHY (Everest family)", go("radio")),
                Command("prs", "PRS signal routing", "Route an internal signal to a GPIO pin", go("radio")),
                Command("save_session", "Save session…", "Save notes, formulas, actions, favorites and history",
                        sessions_vm.saveSession),
                Command("load_session", "Load session…", "Browse saved sessions", sessions_vm.openBrowser),
                Command("tree_search", "Filter the register tree", "Focus the tree's filter box",
                        go("registers", tree_vm.requestSearchFocus)),
            ])
        children: Dict[str, QObject] = {
            "state": state_vm,
            "settings": SettingsViewModel(st, s.registers.clear_cache, s.transfer, ix),
            "hardware": HardwareConfigViewModel(s.hardware),
            "systemInfo": SystemInfoViewModel(self.gateway, st, ix),
            "sessions": sessions_vm,
            "dialogs": self.dialogs,
            "connection": connection_vm,
            "recovery": DisconnectRecoveryViewModel(s.connection, st, s.actions, ix, open_radio_page=go("radio")),
            "tree": tree_vm,
            "readAll": ReadAllViewModel(s.read_all),
            "favorites": FavoritesViewModel(st, s.catalog, s.favorites),
            "detail": detail_vm,
            "formulaEditor": formulas,
            "history": HistoryViewModel(s.history, s.catalog, s.registers, s.actions, ix),
            "actions": actions_vm,
            "actionEditor": editor,
            "log": LogViewModel(s.log, ix),
            "watch": WatchListViewModel(s.watch, s.logger, s.annotations, ix, st),
            "logger": DataLoggerViewModel(s.logger, ix, self.home / ".sirat" / "exports"),
            "sequences": sequences_vm,
            "dumps": dumps_vm,
            "lpwPhy": LpwPhyViewModel(s.phy, st, ix),
            "wifiPhy": WifiPhyViewModel(s.phy, st, ix),
            "prs": PrsViewModel(s.prs, st, ix),
            "palette": palette,
            "windows": WindowsViewModel(),
        }
        return ShellViewModel(children)

    def stop(self) -> None:
        """On exit: one last auto-save, so closing doesn't lose up to 5 minutes of history."""
        self.services.sessions.stop_autosave()
        self.services.sessions.autosave()

    def reload_user_data(self) -> None:
        """After importing or clearing settings: every service re-reads its file (no restart needed)."""
        s = self.services
        self.state.update_preferences(**Preferences.from_json(self.stores.preferences.load()).to_json())
        for service in (s.favorites, s.annotations, s.actions, s.sequences, s.watch, s.logger, s.hardware):
            service.reload()
        self.report_settings_problems()

    def report_settings_problems(self) -> None:
        """Each skipped entry goes to the Log panel; one toast says how many and where the originals are."""
        problems = self.stores.problems()
        if not problems:
            return
        for problem in problems:
            self.services.log.warning(f"Skipped invalid setting: {problem}")
        files = sorted({p.source for p in problems})
        self.interactions.toast("warning", f"Skipped {count(len(problems), 'invalid setting')} in {', '.join(files)}. "
                                           "Details are in the log; the original files are kept as .bak.")

    def start(self, autoconnect: bool = False, position: int = 1) -> None:
        self.services.log.info("SiRAT window initialized")
        self.report_settings_problems()
        self.services.sessions.restore_autosave()  # req 34: "Restored on next launch if exists"
        self.services.sessions.start_autosave()
        self.services.connection.start()
        if autoconnect:
            self.services.connection.connect(position)
