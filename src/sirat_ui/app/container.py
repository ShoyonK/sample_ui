"""ServiceContainer: the composition root. Builds every service and ViewModel and wires them together.

Nothing else in the app constructs services; tests build a container with a fake gateway and a tmp home.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, cast

from PyQt5.QtCore import QObject

from sirat_ui.app.commands import palette_commands
from sirat_ui.app.paths import samples_dir
from sirat_ui.domains.advanced.advanced_viewmodel import AdvancedViewModel
from sirat_ui.domains.advanced.console import ConsoleService
from sirat_ui.domains.advanced.console_viewmodel import ConsoleViewModel
from sirat_ui.domains.advanced.dut_control import DutControlService
from sirat_ui.domains.advanced.dut_control_viewmodel import DutControlViewModel
from sirat_ui.domains.advanced.functions import CustomFunctionService
from sirat_ui.domains.advanced.functions_viewmodel import CustomFunctionsViewModel
from sirat_ui.domains.advanced.memory import MemoryService
from sirat_ui.domains.advanced.memory_viewmodel import MemoryViewModel
from sirat_ui.domains.advanced.session import PythonSession
from sirat_ui.domains.annotations.formula_viewmodel import FormulaEditorViewModel
from sirat_ui.domains.annotations.service import AnnotationService, FavoritesService
from sirat_ui.domains.automation.action_editor import ActionEditorViewModel
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.automation.actions_viewmodel import ActionsViewModel
from sirat_ui.domains.automation.sequences import SequenceService
from sirat_ui.domains.automation.sequences_viewmodel import SequencesViewModel
from sirat_ui.domains.connection.service import ConnectionService
from sirat_ui.domains.connection.system_info_viewmodel import SystemInfoViewModel
from sirat_ui.domains.connection.viewmodels import (ConnectionViewModel, DisconnectRecoveryViewModel,
                                                   FaultRecoveryViewModel)
from sirat_ui.domains.dumps.comparison_viewmodel import ComparisonViewModel
from sirat_ui.domains.dumps.picker_viewmodel import PeripheralPickerViewModel
from sirat_ui.domains.dumps.progress_viewmodel import DumpProgressViewModel
from sirat_ui.domains.dumps.service import DumpService
from sirat_ui.domains.dumps.viewmodel import DumpsViewModel
from sirat_ui.domains.history.service import HistoryLog
from sirat_ui.domains.history.viewmodel import HistoryViewModel
from sirat_ui.domains.instruments.bench import InstrumentBench
from sirat_ui.domains.instruments.chamber import ChamberService
from sirat_ui.domains.instruments.chamber_viewmodel import ChamberViewModel
from sirat_ui.domains.instruments.eca import EcaService
from sirat_ui.domains.instruments.eca_viewmodel import EcaViewModel
from sirat_ui.domains.instruments.packets import PacketService
from sirat_ui.domains.instruments.packets_viewmodel import BlePacketViewModel, GfskPacketViewModel
from sirat_ui.domains.instruments.rf_switch import RfSwitchService
from sirat_ui.domains.instruments.rf_switch_viewmodel import RfSwitchViewModel
from sirat_ui.domains.instruments.siggen import SignalGeneratorService
from sirat_ui.domains.instruments.siggen_viewmodel import SignalGeneratorViewModel
from sirat_ui.domains.logs.service import LogService
from sirat_ui.domains.logs.viewmodel import LogViewModel
from sirat_ui.domains.monitoring.logger import DataLoggerService
from sirat_ui.domains.monitoring.logger_viewmodel import DataLoggerViewModel
from sirat_ui.domains.monitoring.page_guard import MonitoringGuard
from sirat_ui.domains.monitoring.watch import WatchService
from sirat_ui.domains.monitoring.watch_viewmodel import WatchListViewModel
from sirat_ui.domains.radio.phy import PhyService
from sirat_ui.domains.radio.phy_viewmodels import LpwPhyViewModel, WifiPhyViewModel
from sirat_ui.domains.radio.prs import PrsService
from sirat_ui.domains.radio.prs_viewmodel import PrsViewModel
from sirat_ui.domains.registers.catalog import RegisterCatalog
from sirat_ui.domains.registers.detail_viewmodel import RegisterDetailViewModel
from sirat_ui.domains.registers.read_all import ReadAllService
from sirat_ui.domains.registers.read_all_viewmodel import ReadAllViewModel
from sirat_ui.domains.registers.service import RegisterService
from sirat_ui.domains.registers.shortcuts_viewmodel import RegisterShortcutsViewModel
from sirat_ui.domains.registers.tree_viewmodels import FavoritesViewModel, PeripheralTreeViewModel
from sirat_ui.domains.sessions.service import SessionService, count
from sirat_ui.domains.sessions.viewmodel import SessionsViewModel
from sirat_ui.domains.settings.hardware import HardwareConfigService
from sirat_ui.domains.settings.transfer import SettingsTransfer
from sirat_ui.domains.settings.viewmodels import HardwareConfigViewModel, SettingsViewModel
from sirat_ui.domains.shell.command_palette import CommandPaletteViewModel
from sirat_ui.domains.shell.dock import DockViewModel
from sirat_ui.domains.shell.viewmodels import ShellViewModel, StateViewModel, with_children
from sirat_ui.domains.shell.windows import WindowsViewModel
from sirat_ui.gateway.activities import ActivityTracker
from sirat_ui.gateway.port import StationGateway
from sirat_ui.gateway.scheduler import Scheduler
from sirat_ui.models.settings import Preferences
from sirat_ui.shared.dialogs import DialogsViewModel, QmlInteractions
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.shared.highlighter import HighlighterHost
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.state.preferences import PreferencesState
from sirat_ui.state.selection import SelectionState
from sirat_ui.state.station import StationState
from sirat_ui.state.status import StatusLine
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
    bench: InstrumentBench
    siggen: SignalGeneratorService
    rf_switch: RfSwitchService
    chamber: ChamberService
    eca: EcaService
    packets: PacketService
    session: PythonSession
    console: ConsoleService
    functions: CustomFunctionService
    dut_control: DutControlService
    memory: MemoryService


class ServiceContainer:
    def __init__(self, gateway: StationGateway, home: Path, scheduler: Scheduler, backend_label: str = "",
                 interactions: Optional[InteractionService] = None, dumps_dir: Optional[Path] = None) -> None:
        self.gateway = gateway
        self.scheduler = scheduler
        self.home = Path(home)
        self.dumps_dir = Path(dumps_dir) if dumps_dir else self.home / ".sirat" / "dumps"
        self.stores = UserStores.in_home(self.home)
        self.prefs = PreferencesState(Preferences.from_json(self.stores.preferences.load()))
        self.prefs.changed.connect(lambda prefs: self.stores.preferences.save(prefs.to_json()))
        self.state = StationState(self.prefs.value.last_position, backend_label)
        self.state.position_changed.connect(lambda position: self.prefs.update(last_position=position))
        self.selection = SelectionState()
        self.status = StatusLine()

        self.dialogs = DialogsViewModel(is_dark=lambda: self.prefs.value.dark_mode)
        self.interactions: InteractionService = interactions or QmlInteractions(self.dialogs)
        self.highlighters = HighlighterHost()
        self.services = self._build_services()
        self.shell = self._build_viewmodels()
        self.monitoring_guard = self._monitoring_guard()

    def _build_services(self) -> Services:
        log = LogService()
        self.gateway.events.connect(log.on_gateway_event)
        history = HistoryLog()
        errors = ErrorPresenter(self.interactions, log)
        catalog = RegisterCatalog(self.gateway, self.prefs)
        registers = RegisterService(self.gateway, self.state, self.prefs, self.status, history, self.interactions,
                                    errors, log)
        read_all = ReadAllService(registers, log)
        connection = ConnectionService(self.gateway, self.state, catalog, errors, log)
        favorites = FavoritesService(self.stores.favorites)
        annotations = AnnotationService(self.stores.notes, self.stores.formulas)
        watch = WatchService(self.gateway, self.state, catalog, registers, self.stores.watch_list, errors)
        logger = DataLoggerService(self.gateway, self.state, catalog, annotations, self.stores.data_logger, errors,
                                   self.scheduler)
        activities = ActivityTracker(self.gateway)
        actions = ActionService(self.stores.actions, self.gateway, self.state, activities, errors, log,
                                self.stores.custom_functions)
        sequences = SequenceService(self.stores.sequences, actions, self.gateway, self.state, activities, errors, log)
        hardware = HardwareConfigService(self.stores.hardware_config, self.gateway, self.state, log)
        transfer = SettingsTransfer(self.stores, self.reload_user_data)
        dumps = DumpService(self.dumps_dir, catalog, registers, log)
        phy = PhyService(connection, self.state, actions)
        prs = PrsService(self.gateway, self.state, history, actions, errors, log)
        sessions = SessionService(self.home / ".sirat" / "sessions", self.home / ".sirat" / "autosave.json",
                                  annotations, favorites, actions, history, dumps, log, self.scheduler)
        bench = InstrumentBench(self.gateway, self.state, activities, errors, log)
        siggen = SignalGeneratorService(self.gateway, self.state, bench, self.stores.signal_generator, actions, errors,
                                        log)
        rf_switch = RfSwitchService(self.gateway, self.state, bench, actions, errors, log)
        chamber = ChamberService(self.gateway, self.state, bench, errors, log, self.scheduler)
        eca = EcaService(self.gateway, self.state, bench, errors, log)
        packets = PacketService(self.stores.ble_packet, actions, lambda: siggen.instrument_id)
        session = PythonSession(self.gateway, self.state)
        console = ConsoleService(self.gateway, self.state, session, errors)
        functions = CustomFunctionService(self.stores.custom_functions, self.gateway, self.state, session, actions,
                                          errors)
        dut_control = DutControlService(self.gateway, self.state, actions, errors)
        memory = MemoryService(self.gateway, self.state, self.stores.memory_viewer, errors, log)
        return Services(log, history, errors, catalog, registers, read_all, connection, favorites, annotations,
                        watch, logger, actions, sequences, hardware, transfer, dumps, phy, prs, sessions, bench,
                        siggen, rf_switch, chamber, eca, packets, session, console, functions, dut_control, memory)

    def _build_viewmodels(self) -> ShellViewModel:
        """One method per area; each returns the ViewModels it adds, by the name QML uses (app.<name>)."""
        children: Dict[str, QObject] = {}
        for area in (self._shell_viewmodels, self._register_viewmodels, self._automation_viewmodels,
                     self._dumps_viewmodels, self._bench_viewmodels, self._advanced_viewmodels):
            children.update(area())
        children["palette"] = self._palette(children)
        return with_children(children)

    def _monitoring_guard(self) -> MonitoringGuard:
        """The watch list and the logger run only while something on screen shows them."""
        shell = self.shell
        windows = cast(WindowsViewModel, getattr(shell, "windows"))

        def on_page() -> bool:
            return shell.currentPage == "watch" or windows.isOpen("page", "watch")

        def logger_on_screen() -> bool:
            return on_page() or windows.isOpen("logger") or any(k.startswith("graph:") for k in windows.open_keys())

        guard = MonitoringGuard(self.services.watch, self.services.logger, self.services.log, self.interactions,
                                lambda: on_page() or windows.isOpen("watchList"), logger_on_screen)
        shell.changed.connect(guard.check)
        windows.changed.connect(guard.check)
        return guard

    def _go(self, page: str, then: Callable[[], object] = lambda: None) -> Callable[[], None]:
        """A command that opens a page, then does something on it."""
        def run() -> None:
            self.shell.navigate(page)
            then()
        return run

    def _shell_viewmodels(self) -> Dict[str, QObject]:
        s, st, ix = self.services, self.state, self.interactions
        return {
            "state": StateViewModel(st, self.prefs, self.status),
            "settings": SettingsViewModel(st, self.prefs, s.registers.clear_cache, s.transfer, ix),
            "hardware": HardwareConfigViewModel(s.hardware),
            "systemInfo": SystemInfoViewModel(s.connection, st, ix),
            "sessions": SessionsViewModel(s.sessions, ix),
            "dialogs": self.dialogs,
            "connection": ConnectionViewModel(s.connection, st, s.log, s.hardware, ix),
            "recovery": DisconnectRecoveryViewModel(s.connection, st, s.actions, ix, open_radio_page=self._go("radio")),
            "faultRecovery": FaultRecoveryViewModel(s.connection, st, ix),
            "log": LogViewModel(s.log, ix),
            "windows": WindowsViewModel(),
            "dock": DockViewModel(s.history, s.log, s.actions),
        }

    def _register_viewmodels(self) -> Dict[str, QObject]:
        s, st, ix = self.services, self.state, self.interactions
        formulas = FormulaEditorViewModel(s.annotations, ix)
        return {
            "tree": PeripheralTreeViewModel(st, self.selection, self.prefs, s.catalog, s.registers, s.read_all),
            "readAll": ReadAllViewModel(s.read_all, ix),
            "favorites": FavoritesViewModel(st, self.selection, s.catalog, s.favorites),
            "detail": RegisterDetailViewModel(st, self.selection, self.prefs, s.registers, s.favorites, s.annotations,
                                              ix, s.actions.run_finished),
            "registerShortcuts": RegisterShortcutsViewModel(self.selection, s.registers, s.favorites, s.watch,
                                                            s.logger, s.actions, formulas, s.read_all, ix),
            "formulaEditor": formulas,
            "history": HistoryViewModel(s.history, s.catalog, s.registers, s.actions, ix),
            "watch": WatchListViewModel(s.watch, s.logger, s.annotations, ix, self.prefs),
            "logger": DataLoggerViewModel(s.logger, ix, self.home / ".sirat" / "exports"),
        }

    def _automation_viewmodels(self) -> Dict[str, QObject]:
        s, st, ix = self.services, self.state, self.interactions
        editor = ActionEditorViewModel(s.actions, s.catalog, self.prefs, ix)
        return {
            "actions": ActionsViewModel(s.actions, s.sequences, editor, st, ix),
            "actionEditor": editor,
            "sequences": SequencesViewModel(s.sequences, s.actions, st, ix),
        }

    def _dumps_viewmodels(self) -> Dict[str, QObject]:
        s, ix = self.services, self.interactions
        picker, progress = PeripheralPickerViewModel(), DumpProgressViewModel(s.dumps)
        comparison = ComparisonViewModel(self.dumps_dir, ix)
        return {
            "dumps": DumpsViewModel(s.dumps, s.catalog, self.state, self.prefs, ix, picker, progress, comparison,
                                    samples_dir()),
            "dumpPicker": picker,
            "dumpProgress": progress,
            "comparison": comparison,
        }

    def _bench_viewmodels(self) -> Dict[str, QObject]:
        """Radio and PHY page, Instruments page."""
        s, st, ix = self.services, self.state, self.interactions
        return {
            "lpwPhy": LpwPhyViewModel(s.phy, st, ix),
            "wifiPhy": WifiPhyViewModel(s.phy, st, ix),
            "prs": PrsViewModel(s.prs, st, ix),
            "siggen": SignalGeneratorViewModel(s.siggen, s.bench, st, ix),
            "rfSwitch": RfSwitchViewModel(s.rf_switch, s.bench, st, ix),
            "chamber": ChamberViewModel(s.chamber, s.bench, st, ix),
            "eca": EcaViewModel(s.eca, s.bench, st, ix),
            "blePacket": BlePacketViewModel(s.packets, ix),
            "gfsk": GfskPacketViewModel(s.packets, ix),
        }

    def _advanced_viewmodels(self) -> Dict[str, QObject]:
        s, st, ix = self.services, self.state, self.interactions
        return {
            "advanced": AdvancedViewModel(),
            "pyConsole": ConsoleViewModel(s.console, s.session, st),
            "customFunctions": CustomFunctionsViewModel(s.functions, st, ix, self.highlighters),
            "dutControl": DutControlViewModel(s.dut_control, st, ix),
            "memory": MemoryViewModel(s.memory, st, ix),
        }

    def _palette(self, vms: Dict[str, QObject]) -> CommandPaletteViewModel:
        s = self.services
        actions, sequences = cast(ActionsViewModel, vms["actions"]), cast(SequencesViewModel, vms["sequences"])
        commands = palette_commands(
            self._go, cast(ConnectionViewModel, vms["connection"]), cast(StateViewModel, vms["state"]),
            cast(RegisterDetailViewModel, vms["detail"]), cast(PeripheralTreeViewModel, vms["tree"]), actions,
            cast(WatchListViewModel, vms["watch"]), cast(DockViewModel, vms["dock"]), cast(DumpsViewModel, vms["dumps"]),
            cast(AdvancedViewModel, vms["advanced"]), cast(SessionsViewModel, vms["sessions"]))
        return CommandPaletteViewModel(self.selection, s.catalog, s.actions, s.sequences,
                                       navigate=lambda key: self.shell.navigate(key),
                                       select_action=actions.select_name, select_sequence=sequences.select_name,
                                       commands=commands)

    def stop(self) -> None:
        """On exit: one last auto-save, so closing doesn't lose up to 5 minutes of history."""
        self.services.sessions.stop_autosave()
        self.services.sessions.autosave()
        self.services.chamber.stop_polling()

    def reload_user_data(self) -> None:
        """After importing or clearing settings: every service re-reads its file (no restart needed)."""
        s = self.services
        self.prefs.update(**Preferences.from_json(self.stores.preferences.load()).to_json())
        for service in (s.favorites, s.annotations, s.actions, s.sequences, s.watch, s.logger, s.hardware, s.siggen,
                        s.packets, s.functions, s.memory):
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
