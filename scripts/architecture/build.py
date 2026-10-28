"""Writes docs/ARCHITECTURE.md from the code. Run from the repo root: uv run python scripts/architecture/build.py

Class members and constructors come from sigs.py, arrows from constructor parameter types, and the endpoint
map from callgraph.py (each ViewModel slot traced through the services to the gateway)."""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), "src"]
import callgraph  # noqa: E402
import flowstyle  # noqa: E402
import sigs  # noqa: E402
from sirat_ui.core.requires import METHOD_REQUIRES  # noqa: E402

D = "sirat_ui.domains"
G = "sirat_ui.gateway"

FIXES = {   # signatures the extractor can't read (**kwargs, *args)
    ("PreferencesState", "+update()"): "+update(**changes)",
    ("Event", "+emit()"): "+emit(*args)",
}


def class_block(module: str, cls: str, show_ctor: bool = True) -> list:
    ms = sigs.members(module, cls)
    if cls.endswith("ViewModel"):
        props = [m for m in ms if "(" not in m]
        ms = [m for m in ms if "(" in m] + ([f"+{len(props)} bindable properties"] if props else [])
    ms = [FIXES.get((cls, m), m) for m in ms]
    lines = [f"    class {cls} {{"]
    if show_ctor:
        ctor = sigs.ctor(module, cls)
        if not ctor.endswith("()"):
            lines.append(f"        +{ctor}")
    lines += [f"        {m}" for m in ms]
    lines.append("    }")
    return lines


def ctor_types(module: str, cls: str) -> list:
    """(param, type) pairs of the constructor."""
    sig = sigs.ctor(module, cls)
    inner = sig[sig.index("(") + 1:-1]
    out = []
    for part in re.split(r",\s*(?![^~]*~)", inner):
        if ":" in part:
            name, typ = part.split(":", 1)
            typ = typ.split("=")[0].strip().rstrip("?")
            out.append((name.strip(), typ))
    return out


# Diagram title -> direction, where render_check.py measured the flipped layout closer to 4:3.
DIRECTIONS = {
    "DUT, registers, memory, Python": "LR",
    "Long-running work, instruments, and the plumbing": "LR",
    "8. Shared state": "LR",
    "9. Shell: pages, navigation, Ctrl+K": "LR",
    "11. Watch and logger": "LR",
    "Instruments: services": "LR",
    "Advanced: services": "LR",
}


def class_diagram(title: str, intro: str, specs: list, extra: list = (), direction: str = "TB",
                  heading: str = "##", stubs: tuple = ()) -> str:
    """specs get full boxes; stubs (names) get empty boxes, so arrows to them stay without the clutter."""
    direction = DIRECTIONS.get(title, direction)
    names = {s.split(":")[1] for s in specs} | set(stubs)
    body = []
    ctors = []
    for s in specs:
        mod, cls = s.split(":")
        body += class_block(mod, cls, show_ctor=False)
        c = sigs.ctor(mod, cls)
        if not c.endswith("()"):
            ctors.append(c)
    body += [f"    class {name}" for name in stubs]
    arrows = []
    for s in specs:
        mod, cls = s.split(":")
        for param, typ in ctor_types(mod, cls):
            if typ in names and typ != cls:
                arrows.append(f"    {cls} --> {typ} : {param}")
    lines = ["```mermaid", "classDiagram", f"    direction {direction}"] + body + arrows + list(extra) + ["```"]
    ctor_text = ""
    if ctors:
        ctor_text = ("\n<details><summary>Constructors</summary>\n\n```text\n" + "\n".join(ctors)
                     + "\n```\n\n</details>\n")
    return f"{heading} {title}\n\n{intro}\n\n" + "\n".join(lines) + "\n" + ctor_text


def subsystem(title: str, intro: str, services: list, viewmodels: list, extra_services: list = (),
              extra_viewmodels: list = ()) -> str:
    """Two diagrams: the services with full signatures, then the ViewModels with the services as name-only boxes."""
    service_names = [s.split(":")[1] for s in services]
    used = []
    for s in viewmodels:
        mod, cls = s.split(":")
        for _, typ in ctor_types(mod, cls):
            if typ in service_names and typ not in used:
                used.append(typ)
    return (f"## {title}\n\n{intro}\n\n"
            + class_diagram(f"{title.split(' ', 1)[1]}: services", "Constructor arrows between services.",
                            services, list(extra_services), heading="###")
            + "\n"
            + class_diagram(f"{title.split(' ', 1)[1]}: ViewModels",
                            "Slots QML calls; the services they use are shown by name (members above).",
                            viewmodels, list(extra_viewmodels) + ["    %% wrap 3"], heading="###", stubs=tuple(used)))


sections = []

# --------------------------------------------------------------------------------------------- overview
sections.append("""# SiRAT frontend architecture

Generated from the code by `scripts/architecture/build.py`; rerun it after changing classes or station calls. Class boxes list public methods with their signatures. An arrow
`A --> B : name` means A's constructor takes a B called `name`; each diagram's full constructors are listed
under it.
ViewModel boxes list their Qt slots (what QML calls) and how many bindable properties they expose.
Types: `X?` is Optional, `Call[T]` is the async result of one station request. Dashed boxes are classes
detailed in another diagram. Arrows are drawn right-angled (one bend where possible) to keep crowded diagrams readable.

Contents

1. [Layers](#1-layers)
2. [Dependency rules](#2-dependency-rules)
3. [How the app is assembled](#3-how-the-app-is-assembled)
4. [Request flow: reading a register](#4-request-flow-reading-a-register)
5. [Request flow: running an action](#5-request-flow-running-an-action)
6. [Station interfaces (gateway)](#6-station-interfaces-gateway)
7. [The fake station](#7-the-fake-station)
8. [Shared state](#8-shared-state)
9. [Shell: pages, navigation, Ctrl+K](#9-shell-pages-navigation-ctrlk)
10. [Registers page](#10-registers-page)
11. [Watch and logger](#11-watch-and-logger)
12. [Actions and sequences](#12-actions-and-sequences)
13. [Dumps and Radio Calculator diff](#13-dumps-and-radio-calculator-diff)
14. [Radio and PHY](#14-radio-and-phy)
15. [Instruments](#15-instruments)
16. [Advanced](#16-advanced)
17. [Connection, settings, sessions, log](#17-connection-settings-sessions-log)
18. [ViewModels to backend endpoints](#18-viewmodels-to-backend-endpoints)

See [EXTENDING.md](EXTENDING.md) for how to add a page, an operation kind, a service or an endpoint.
""")

sections.append("""## 1. Layers

QML only talks to ViewModels. ViewModels talk to services and state. Services are the only code that calls the
station, through the area interfaces in `gateway/port.py`. Everything below the ViewModels is pure Python (no
Qt). `models/`, `core/` and `stores/` are shared helpers any layer may use.

```mermaid
flowchart TB
    qml["<b>QML</b> · qml/<br/>*.ui.qml forms (layout only) + *.qml wrappers (bind properties, call slots)"]
    vm["<b>ViewModels</b> · domains/*/…viewmodel.py<br/>ShellViewModel is app; app.detail, app.dumps, … one per card, panel or dialog"]
    svc["<b>Services</b> · domains/*<br/>one per area: RegisterService, ActionService, ChamberService, …"]
    gw["<b>Gateway</b> · gateway/<br/>area interfaces (RegistersPort, InstrumentsPort, …) · ActivityTracker"]
    fake["<b>FakeStationGateway</b><br/>in memory, today"]
    api["<b>ApiStationGateway</b><br/>client SDK, later"]
    state["<b>State</b> · state/<br/>StationState · SelectionState<br/>PreferencesState · StatusLine"]
    base["<b>Shared helpers</b><br/>models/ dataclasses · core/ pure functions<br/>stores/ ~/.sirat JSON files"]

    qml -->|"properties, slots"| vm
    vm -->|"method calls"| svc
    svc -->|"calls → Call"| gw
    gw --> fake
    gw -.-> api
    vm -.-> state
    svc -.-> state
    fake -.->|"events: status, activity, watch, log"| gw
    svc ~~~ base
```
""")

sections.append("""## 2. Dependency rules

Each layer may import the layers below it, never above. The rules on the right are checked by
`tests/unit/test_architecture.py`.

```mermaid
flowchart TB
    subgraph stack["Who may import whom (top to bottom)"]
        direction TB
        qml["QML"] --> vm["ViewModels"]
        vm --> svc["Services"]
        svc --> ports["gateway/port.py: area interfaces"]
        ports --> state["state/ · core/ · stores/"]
        state --> models["models/: stdlib only (+ core.bits, core.formatting, gateway.errors)"]
        app["app/: composition root, may see StationGateway"] -.-> svc
        fake["gateway/fake: implements StationGateway"] -.-> ports
    end
    subgraph rules["Checked by tests"]
        direction TB
        r1["No PyQt5 in core, state, stores, gateway, services"]
        r2["ViewModels never import gateway.port or ErrorPresenter"]
        r3["Only app/ and gateway/ name StationGateway"]
        r4["One Qt property style: qprop or @pyqtProperty"]
        r5[".ui.qml forms: no handlers; every control has an objectName"]
        r6["No Python file over 600 lines"]
        r1 ~~~ r2 ~~~ r3 ~~~ r4 ~~~ r5 ~~~ r6
    end
    stack ~~~ rules
    classDef rule fill:#fff4e5,stroke:#c76a00,color:#5a3000
    class r1,r2,r3,r4,r5,r6 rule
```
""")

sections.append("""## 3. How the app is assembled

`ServiceContainer` (app/container.py) is the only place that constructs services and ViewModels.

```mermaid
flowchart TB
    launch["launch.py · build_app(backend, scenario)"] --> gw["FakeStationGateway(scheduler)"]
    launch --> container["ServiceContainer(gateway, home, scheduler)"]
    subgraph init["ServiceContainer.__init__"]
        direction TB
        stores["UserStores.in_home(home)<br/>~/.sirat JSON files"]
        st["PreferencesState → StationState<br/>SelectionState · StatusLine"]
        services["_build_services() → Services<br/>LogService, ErrorPresenter, ActivityTracker,<br/>RegisterCatalog, RegisterService, …"]
        subgraph vms["_build_viewmodels()"]
            direction LR
            a1["_shell_viewmodels()"] ~~~ a2["_register_viewmodels()"] ~~~ a3["_automation_viewmodels()"]
            a4["_dumps_viewmodels()"] ~~~ a5["_bench_viewmodels()"] ~~~ a6["_advanced_viewmodels()"]
            pal["_palette() → palette_commands()"]
        end
        shell["with_children(children) → ShellViewModel<br/>one constant property per child: app.&lt;name&gt;"]
        stores --> st --> services --> vms --> shell
    end
    container --> init
    shell --> app["Application: setContextProperty('app', shell), load qml/Main.qml"]
    app --> start["container.start(): restore autosave,<br/>ConnectionService.start(): sys.hello, sys.subscribe, sys.status"]
```
""")

sections.append("""## 4. Request flow: reading a register

```mermaid
sequenceDiagram
    actor User
    participant QML as RegisterDetail.qml
    participant VM as RegisterDetailViewModel
    participant RS as RegisterService
    participant Port as RegistersPort (gateway)
    participant Station as Station (fake or real)
    participant H as HistoryLog
    participant S as StatusLine

    User->>QML: clicks Read
    QML->>VM: read()
    VM->>RS: read(reg, manual=True)
    RS->>Port: read_register(position, name)
    Port->>Station: registers.read
    Station-->>Port: value
    Port-->>RS: Call resolves with value
    RS->>H: record("read", register, value)
    RS->>S: set("BUFC.LPMODE @ 0x… · read ok")
    RS-->>VM: value_changed(full_name, value)
    VM-->>QML: changed → valueText, bitValues, fields
    Note over RS,Station: On failure RS calls ErrorPresenter.present(error, context): one log line and one toast
```
""")

sections.append("""## 5. Request flow: running an action

```mermaid
sequenceDiagram
    actor User
    participant VM as ActionsViewModel
    participant AS as ActionService
    participant Ops as core/ops.py + wire_ops.py
    participant Port as AutomationPort
    participant T as ActivityTracker
    participant Station as Station

    User->>VM: runSelected()
    VM->>AS: run(names)
    AS->>Ops: action_ops(action, …) → to_wire(op, functions) per op
    Ops-->>AS: wire ops (custom function code copied in, sequences expanded)
    AS->>Port: run_sequence(position, ops, stop_on_error=True)
    Port->>Station: automation.seq.run
    Station-->>AS: activity_id
    AS->>T: follow(activity_id, _progress, _finished)
    loop each op
        Station-->>T: activity.progress (step, total, message)
        T-->>AS: _progress(event) → console line
    end
    Station-->>T: activity.finished (ok, results, error)
    T-->>AS: _finished(label, event)
    AS-->>VM: run_finished(ok), console lines
```
""")

sections.append("""## 6. Station interfaces (gateway)

One interface per API area. A service declares the one it uses; `StationGateway` combines them for the
composition root and the backends. `ConnectionGateway` (connection/service.py) is `SystemPort + DutPort`.

```mermaid
flowchart RL
    ES["EventSource<br/>events: Event"]
    SP["SystemPort"] --> ES
    RP["RegistersPort"] --> ES
    AP["ActivityPort"] --> ES
    AU["AutomationPort"] --> AP
    IP["InstrumentsPort"] --> AP
    DP["DutPort"]
    RF["RfPort"]
    MP["MemoryPort"]
    ADV["AdvancedPort"]
    SG["StationGateway<br/>(all areas)"]
    SG --> SP & DP & RF & RP & AU & IP & MP & ADV
    CG["ConnectionGateway"] --> SP & DP
```
""")

sections.append(class_diagram(
    "DUT, registers, memory, Python",
    "The calls about one DUT position.",
    [f"{G}.port:SystemPort", f"{G}.port:DutPort", f"{G}.port:RfPort", f"{G}.port:RegistersPort",
     f"{G}.port:MemoryPort", f"{G}.port:AdvancedPort"], heading="###"))

sections.append(class_diagram(
    "Long-running work, instruments, and the plumbing",
    "Sequence runs, chamber waits and ECA captures are activities: the start call returns an activity id and "
    "`activity.progress` / `activity.finished` events follow, routed by `ActivityTracker`. `Call` is the async "
    "result every port method returns.",
    [f"{G}.port:ActivityPort", f"{G}.port:AutomationPort", f"{G}.port:InstrumentsPort", f"{G}.call:Call",
     f"{G}.activities:ActivityTracker"],
    extra=["    ActivityPort <|-- AutomationPort", "    ActivityPort <|-- InstrumentsPort"], heading="###"))

sections.append("""## 7. The fake station

`FakeStationGateway` implements `StationGateway` in memory, enforces the same requires rules as the real
service (`core/requires.py`) and returns the same error codes. It composes one part per area.

```mermaid
classDiagram
    direction TB
    class FakeStationGateway {
        +set_latency(method: str, ms: int)
        +fail_next(method: str, code: ErrorCode, message: str='', data: Dict?=None)
        +time_out_next(method: str, late_ms: int=1500)
        +drop_dut(position: int, cause: str='RPC connection lost', detected_by: str='heartbeat')
        +drop_instrument(instrument_id: str)
        +release(count: int?=None)
        +emit_watch_tick(sub_id: str?=None)
        +calls_to(method: str) List~RecordedCall~
        +all StationGateway methods
    }
    class AdvancedMethods {
        <<mixin>>
        +memory_* and console_*, custom_function, dut_control_* → self.advanced
    }
    class FakeAdvanced {
        +sessions Dict~str,ConsoleSession~
        +duts Dict~int,FakeDut~
        +exec_time_limit_s float
        +dut(position: int) FakeDut
        +end_sessions(position: int)
        +run_op(position: int, kind: str, op: Dict) Any
    }
    class FakeBench {
        +instruments, siggen, chamber, ECA, RF switch state
        +require(kind: str, id: str?) InstrumentFacts
        +drop(id: str)
        +abort(activity_id: str) bool
    }
    class FakeSequencer {
        +start(activity: FakeActivity)
        +abort(activity_id: str)
    }
    class RegisterMemory {
        +read(name: str) int
        +write(name: str, value: int) int
        +field_insert(name: str, field: str, value: int) int
    }
    class FakeMemory {
        +read(address: int, size: int) Tuple~int,bytes~
        +write(address: int, value: int, size: int) int
    }
    class FakeDut {
        +dut_control, rpc_io, rm, rta
        +method(path: str) Callable?
    }
    AdvancedMethods <|-- FakeStationGateway
    FakeStationGateway *-- FakeAdvanced : advanced
    FakeStationGateway *-- FakeBench : bench
    FakeStationGateway *-- FakeSequencer : sequencer
    FakeStationGateway *-- RegisterMemory : memory
    FakeAdvanced *-- FakeMemory : ram
    FakeAdvanced *-- FakeDut : duts
    FakeMemory --> RegisterMemory : peripheral window
```

<details><summary>Constructors</summary>

```text
FakeStationGateway(scheduler: Scheduler?=None, peripherals: List[PeripheralDef]?=None, seed: int=7, clock: Callable=time.time)
FakeAdvanced(respond: Respond, log: Log, host: AdvancedHost, peripherals: List[PeripheralDef], seed: int)
FakeBench(scheduler: Scheduler, emit: Callable, log: Callable, emit_status: Callable, clock: Callable, chip: Callable)
```

</details>
""")

sections.append(class_diagram(
    "8. Shared state",
    "Four small stores, each with its own change event, so a status message doesn't refresh pages that only "
    "care about the DUT. `Event` is the plain-Python signal the services and stores use (Qt-free).",
    ["sirat_ui.state.station:StationState", "sirat_ui.state.selection:SelectionState",
     "sirat_ui.state.preferences:PreferencesState", "sirat_ui.state.status:StatusLine",
     "sirat_ui.core.observable:Event"],
    extra=["    StationState ..> Event : changed, disconnected, position_changed",
           "    SelectionState ..> Event : changed",
           "    PreferencesState ..> Event : changed", "    StatusLine ..> Event : changed"]))

sections.append(class_diagram(
    "9. Shell: pages, navigation, Ctrl+K",
    "`domains/shell/pages.py` holds the page table (key, title, icon, QML file). `with_children()` turns "
    "every registered ViewModel into a constant `app.<name>` property. `app/commands.py` builds the Ctrl+K list.",
    ["sirat_ui.app.container:ServiceContainer", f"{D}.shell.viewmodels:ShellViewModel",
     f"{D}.shell.viewmodels:StateViewModel", f"{D}.shell.command_palette:CommandPaletteViewModel",
     f"{D}.shell.dock:DockViewModel", f"{D}.shell.windows:WindowsViewModel"],
    extra=["    class pages_py {", "        <<module domains/shell/pages.py>>", "        +PAGES List~Dict~",
           "        +page_source(key: str) str", "    }",
           "    class commands_py {", "        <<module app/commands.py>>",
           "        +palette_commands(go, connection, state, detail, tree, actions, watch, dock, dumps, advanced, sessions) List~Command~",
           "    }",
           "    ServiceContainer ..> ShellViewModel : with_children(children)",
           "    ServiceContainer ..> commands_py", "    ShellViewModel ..> pages_py",
           "    ShellViewModel o-- StateViewModel", "    ShellViewModel o-- CommandPaletteViewModel",
           "    ShellViewModel o-- DockViewModel", "    ShellViewModel o-- WindowsViewModel"],
    direction="TB"))

sections.append(subsystem(
    "10. Registers page",
    "Tree and favorites select a register (`SelectionState`); the detail panel shows and edits it; the "
    "shortcuts ViewModel sends it elsewhere (favorites, watch, logger, formulas, Actions).",
    [f"{D}.registers.catalog:RegisterCatalog", f"{D}.registers.service:RegisterService",
     f"{D}.registers.read_all:ReadAllService", f"{D}.annotations.service:AnnotationService",
     f"{D}.annotations.service:FavoritesService", f"{D}.history.service:HistoryLog"],
    [f"{D}.registers.tree_viewmodels:PeripheralTreeViewModel", f"{D}.registers.tree_viewmodels:FavoritesViewModel",
     f"{D}.registers.detail_viewmodel:RegisterDetailViewModel",
     f"{D}.registers.shortcuts_viewmodel:RegisterShortcutsViewModel",
     f"{D}.registers.read_all_viewmodel:ReadAllViewModel", f"{D}.history.viewmodel:HistoryViewModel",
     f"{D}.annotations.formula_viewmodel:FormulaEditorViewModel"],
    extra_viewmodels=["    RegisterShortcutsViewModel --> FormulaEditorViewModel : formula_editor"]))

sections.append(class_diagram(
    "11. Watch and logger",
    "Both use a `WatchSubscription` (registers.watch / registers.unwatch); values arrive as `WatchValues` events.",
    [f"{D}.monitoring.watch:WatchService", f"{D}.monitoring.logger:DataLoggerService",
     f"{D}.monitoring.subscription:WatchSubscription", f"{D}.monitoring.watch_viewmodel:WatchListViewModel",
     f"{D}.monitoring.logger_viewmodel:DataLoggerViewModel"],
    extra=["    WatchService *-- WatchSubscription : _sub", "    DataLoggerService *-- WatchSubscription : _sub"]))

sections.append(class_diagram(
    "12. Actions and sequences",
    "Every operation kind is one `OpKind` in `core/ops.py` (`KINDS`), used by `describe_op(op)`, "
    "`code_lines(op, functions)` (code generation) and `to_wire(op, functions)` (automation.seq.run). "
    "Pages that offer Add to Actions depend on `ActionRecorder`.",
    [f"{D}.automation.actions:ActionService", f"{D}.automation.sequences:SequenceService",
     f"{D}.automation.recorder:ActionRecorder", "sirat_ui.gateway.activities:ActivityTracker",
     "sirat_ui.core.ops:OpKind", f"{D}.automation.actions_viewmodel:ActionsViewModel",
     f"{D}.automation.sequences_viewmodel:SequencesViewModel",
     f"{D}.automation.action_editor:ActionEditorViewModel"],
    extra=["    class ops_py {", "        <<module core/ops.py>>", "        +KINDS Dict~str,OpKind~",
           "        +op_kind(op: Op) str", "        +describe_op(op: Op) str",
           "        +code_lines(op: Op, functions: Functions) List~str~",
           "        +to_wire(op: Op, functions: Functions) Op", "        +carries_code(kind: str) bool",
           "        +editable(kind: str) bool", "    }",
           "    class wire_ops_py {", "        <<module core/wire_ops.py>>",
           "        +action_ops(action: Action, actions: Callable, custom_functions: Mapping) List~Dict~", "    }",
           "    ActionRecorder <|.. ActionService", "    ops_py o-- OpKind", "    wire_ops_py ..> ops_py",
           "    ActionService ..> wire_ops_py", "    ActionEditorViewModel ..> ops_py"]))

sections.append(class_diagram(
    "13. Dumps and Radio Calculator diff",
    "`DumpsViewModel` starts the work; the picker, the progress dialog and the comparison card are separate "
    "ViewModels it drives.",
    [f"{D}.dumps.service:DumpService", f"{D}.dumps.viewmodel:DumpsViewModel",
     f"{D}.dumps.picker_viewmodel:PeripheralPickerViewModel", f"{D}.dumps.progress_viewmodel:DumpProgressViewModel",
     f"{D}.dumps.comparison_viewmodel:ComparisonViewModel"]))

sections.append(class_diagram(
    "14. Radio and PHY",
    "PHY loading goes through `ConnectionService.load_phy` (dut.load_phy); PRS routing through `RfPort`.",
    [f"{D}.radio.phy:PhyService", f"{D}.radio.prs:PrsService", f"{D}.radio.phy_viewmodels:LpwPhyViewModel",
     f"{D}.radio.phy_viewmodels:WifiPhyViewModel", f"{D}.radio.prs_viewmodel:PrsViewModel"]))

sections.append(subsystem(
    "15. Instruments",
    "`InstrumentBench` finds the instrument of each kind in `StationState.instruments` and follows instrument "
    "activities (chamber waits, ECA captures) through the shared `ActivityTracker`.",
    [f"{D}.instruments.bench:InstrumentBench", f"{D}.instruments.siggen:SignalGeneratorService",
     f"{D}.instruments.rf_switch:RfSwitchService", f"{D}.instruments.chamber:ChamberService",
     f"{D}.instruments.eca:EcaService", f"{D}.instruments.packets:PacketService"],
    [f"{D}.instruments.instrument_viewmodel:InstrumentViewModel",
     f"{D}.instruments.siggen_viewmodel:SignalGeneratorViewModel",
     f"{D}.instruments.rf_switch_viewmodel:RfSwitchViewModel",
     f"{D}.instruments.chamber_viewmodel:ChamberViewModel", f"{D}.instruments.eca_viewmodel:EcaViewModel",
     f"{D}.instruments.packets_viewmodel:BlePacketViewModel",
     f"{D}.instruments.packets_viewmodel:GfskPacketViewModel"],
    extra_viewmodels=["    InstrumentViewModel <|-- SignalGeneratorViewModel", "    InstrumentViewModel <|-- RfSwitchViewModel",
                      "    InstrumentViewModel <|-- ChamberViewModel", "    InstrumentViewModel <|-- EcaViewModel"]))

sections.append(subsystem(
    "16. Advanced",
    "The console and custom functions share one station-side Python session per DUT (`PythonSession`).",
    [f"{D}.advanced.session:PythonSession", f"{D}.advanced.console:ConsoleService",
     f"{D}.advanced.functions:CustomFunctionService", f"{D}.advanced.dut_control:DutControlService",
     f"{D}.advanced.memory:MemoryService", f"{D}.advanced.output:OutputLog"],
    [f"{D}.advanced.advanced_viewmodel:AdvancedViewModel", f"{D}.advanced.console_viewmodel:ConsoleViewModel",
     f"{D}.advanced.functions_viewmodel:CustomFunctionsViewModel",
     f"{D}.advanced.dut_control_viewmodel:DutControlViewModel", f"{D}.advanced.memory_viewmodel:MemoryViewModel"],
    extra_services=["    ConsoleService *-- OutputLog : output", "    CustomFunctionService *-- OutputLog : output",
                    "    DutControlService *-- OutputLog : output"]))

sections.append(subsystem(
    "17. Connection, settings, sessions, log",
    "`ErrorPresenter` is how services report station failures: one log line and one toast.",
    [f"{D}.connection.service:ConnectionService", f"{D}.settings.hardware:HardwareConfigService",
     f"{D}.sessions.service:SessionService", f"{D}.settings.transfer:SettingsTransfer",
     "sirat_ui.shared.error_presenter:ErrorPresenter", f"{D}.logs.service:LogService"],
    [f"{D}.connection.viewmodels:ConnectionViewModel", f"{D}.connection.viewmodels:DisconnectRecoveryViewModel",
     f"{D}.connection.system_info_viewmodel:SystemInfoViewModel", f"{D}.settings.viewmodels:SettingsViewModel",
     f"{D}.settings.viewmodels:HardwareConfigViewModel", f"{D}.sessions.viewmodel:SessionsViewModel",
     f"{D}.logs.viewmodel:LogViewModel"]))

# --------------------------------------------------------------------------------- endpoint map
vm_eps, api, _ = callgraph.compute()   # ViewModel -> endpoints, gateway method -> API name
all_eps = sorted(set(api.values()))
PAGE = {
    "Registers": ["PeripheralTreeViewModel", "RegisterDetailViewModel", "RegisterShortcutsViewModel", "HistoryViewModel"],
    "Watch": ["WatchListViewModel", "DataLoggerViewModel"],
    "Actions and sequences": ["ActionsViewModel", "SequencesViewModel"],
    "Dumps": ["DumpsViewModel"],
    "Radio": ["LpwPhyViewModel", "WifiPhyViewModel", "PrsViewModel"],
    "Instruments": ["InstrumentViewModel", "SignalGeneratorViewModel", "RfSwitchViewModel", "ChamberViewModel",
                    "EcaViewModel"],
    "Advanced": ["ConsoleViewModel", "CustomFunctionsViewModel", "DutControlViewModel", "MemoryViewModel"],
    "Connection and settings": ["ConnectionViewModel", "DisconnectRecoveryViewModel", "FaultRecoveryViewModel",
                                "SystemInfoViewModel", "HardwareConfigViewModel"],
}
listed = {v for vs in PAGE.values() for v in vs}
assert set(vm_eps) <= listed, set(vm_eps) - listed
user_eps = {e for es in vm_eps.values() for e in es}
BACKGROUND = callgraph.SERVICE_CALLS
UNUSED = sorted(set(all_eps) - user_eps - set(BACKGROUND))


def nid(s):
    return re.sub(r"\W", "_", s)


NS_ORDER = ["sys", "dut", "registers", "rf", "automation", "activity", "instruments", "memory", "advanced"]
ov = ["```mermaid", "flowchart LR"]
for page in PAGE:
    ov.append(f'    {nid(page)}["{page}"]')
for ns in NS_ORDER:
    total = len(by_ns.get(ns, [])) if False else len([e for e in all_eps if e.split(".")[0] == ns])
    ov.append(f'    ns_{ns}[["{ns}.* ({total})"]]')
for page, vms in PAGE.items():
    counts = {}
    for v in vms:
        for e in vm_eps.get(v, []):
            counts.setdefault(e.split(".")[0], set()).add(e)
    for ns, es in counts.items():
        ov.append(f"    {nid(page)} -->|{len(es)}| ns_{ns}")
ov += ['    bgsvc["services on their own<br/>startup, live watch, connects"]',
       "    bgsvc -.-> ns_sys", "    bgsvc -.-> ns_registers", "    bgsvc -.-> ns_rf", "    bgsvc -.-> ns_instruments",
       "    bgsvc -.-> ns_dut", "```"]

per_page = []
for page, vms in PAGE.items():
    eps = sorted({e for v in vms for e in vm_eps.get(v, [])})
    if not eps:
        continue
    d = ["```mermaid", "flowchart LR"]
    for v in vms:
        if vm_eps.get(v):
            d.append(f'    {nid(v)}["{v}"]')
    for e in eps:
        d.append(f'    {nid(e)}(["{e}"])')
    for v in vms:
        for e in vm_eps.get(v, []):
            d.append(f"    {nid(v)} --> {nid(e)}")
    d.append("```")
    per_page.append(f"### {page}\n\n" + "\n".join(d) + "\n")

bg = ["```mermaid", "flowchart LR"]
for e, (who, when) in BACKGROUND.items():
    bg.append(f'    {nid(e)}(["{e}"])')
for who in sorted({w for w, _ in BACKGROUND.values()}):
    bg.append(f'    {nid(who)}["{who}"]')
for e, (who, when) in BACKGROUND.items():
    bg.append(f"    {nid(who)} -->|{when}| {nid(e)}")
bg.append("```")

events = """| Event (pushed after `sys.subscribe`) | Who listens | What it does |
|---|---|---|
| `status.changed` (`StatusChanged`) | ConnectionService | `StationState.apply_status`: facts per position, instruments |
| `dut.disconnected` (`DutDisconnected`) | ConnectionService | `StationState.mark_disconnected`; recovery dialog, sessions end |
| `watch.values` (`WatchValues`) | WatchService, DataLoggerService | new values for the watch list and the logger plot |
| `activity.progress`, `activity.finished` | ActivityTracker → ActionService, SequenceService, InstrumentBench | run and instrument progress |
| `log` (`LogLine`) | LogService | the Log panel |
| `call.late` (`CallLate`) | LogService | how a call that timed out finally ended |"""

table = ["| Endpoint | Gateway method | Requires | Called by |", "|---|---|---|---|"]
rev_api = {}
for m, e in api.items():
    rev_api.setdefault(e, m)
for e in all_eps:
    callers = sorted(v for v, eps in vm_eps.items() if e in eps)
    if e in BACKGROUND:
        callers.append(f"{BACKGROUND[e][0]} ({BACKGROUND[e][1]})")
    who = ", ".join(callers) if callers else "not used by the frontend yet"
    req = ", ".join(METHOD_REQUIRES.get(e, ())) or "—"
    table.append(f"| `{e}` | `{rev_api[e]}` | {req} | {who} |")

sections.append(f"""## 18. ViewModels to backend endpoints

What the real station service must answer for each screen to work. Solid arrows are calls a user action
triggers, traced from each ViewModel slot through the services to the gateway (`callgraph`, not hand-drawn).
{len(all_eps)} endpoints in total; the ones marked
⚠ unused are in the API design but no screen calls them yet ({', '.join(UNUSED) or 'none'}).

### Overview: pages to API areas

Arrow labels are how many endpoints of that area the page calls.

{chr(10).join(ov)}

{chr(10).join(per_page)}
### Calls services make on their own

{chr(10).join(bg)}

### Events

{events}

### All endpoints

{chr(10).join(table)}

"Requires" is the client's copy of the service's rule table (`core/requires.py`); the GUI disables a button
while a requirement is missing and the service refuses the call with `wrong_state`.
""")

out = Path("docs/ARCHITECTURE.md")
out.write_text(flowstyle.restyle("\n".join(sections)), encoding="utf-8")
print("wrote", out, len(out.read_text(encoding="utf-8").splitlines()), "lines")
