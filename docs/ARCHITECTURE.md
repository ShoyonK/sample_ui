# SiRAT frontend architecture

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

## 1. Layers

QML only talks to ViewModels. ViewModels talk to services and state. Services are the only code that calls the
station, through the area interfaces in `gateway/port.py`. Everything below the ViewModels is pure Python (no
Qt). `models/`, `core/` and `stores/` are shared helpers any layer may use.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
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

## 2. Dependency rules

Each layer may import the layers below it, never above. The rules on the right are checked by
`tests/unit/test_architecture.py`.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
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

## 3. How the app is assembled

`ServiceContainer` (app/container.py) is the only place that constructs services and ViewModels.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
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

## 4. Request flow: reading a register

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

## 5. Request flow: running an action

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

## 6. Station interfaces (gateway)

One interface per API area. A service declares the one it uses; `StationGateway` combines them for the
composition root and the backends. `ConnectionGateway` (connection/service.py) is `SystemPort + DutPort`.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
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

### DUT, registers, memory, Python

The calls about one DUT position.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    SystemPort["<b>SystemPort</b><hr/>+hello() Call<br/>+status() Call<br/>+subscribe(topics: List[str]) Call<br/>+recover(position: int) Call"]:::box
    DutPort["<b>DutPort</b><hr/>+connect_dut(position: int, config_type: str, config_file: str, rpc: RpcAddress?=None) Call<br/>+reconnect_dut(position: int) Call[None]<br/>+disconnect_dut(position: int) Call<br/>+probe(position: int, rpc: RpcAddress?, timeout_s: float) Call[ProbeResult]<br/>+load_phy(position: int, phy: PhySpec) Call[LoadPhyResult]<br/>+dut_info(position: int) Call<br/>+set_rpc_timeout(seconds: float) Call"]:::box
    RfPort["<b>RfPort</b><hr/>+rf_paths() Call[List of str]<br/>+rf_connect(position: int, path: str) Call[None]<br/>+rf_disconnect(position: int) Call[None]<br/>+prs_route(position: int, route: PrsRoute) Call[None]<br/>+prs_signals(position: int) Call[PrsSignalCatalog]"]:::box
    RegistersPort["<b>RegistersPort</b><hr/>+register_tree(position: int) Call<br/>+read_register(position: int, name: str) Call<br/>+read_many(position: int, names: List[str], include_read_sensitive: bool=False) Call<br/>+write_register(position: int, name: str, value: int, confirm: bool=False, verify: bool=True) Call<br/>+write_field(position: int, name: str, field: str, value: int, confirm: bool=False, verify: bool=True) Call<br/>+watch(position: int, names: List[str], interval_s: float, include_read_sensitive: bool=False) Call<br/>+unwatch(sub_id: str) Call"]:::box
    MemoryPort["<b>MemoryPort</b><hr/>+memory_read(position: int, address: int, size: int) Call[MemoryBlock]<br/>+memory_write(position: int, address: int, value: int, size: int) Call[MemoryWriteRes]"]:::box
    AdvancedPort["<b>AdvancedPort</b><hr/>+console_open(position: int) Call[str]<br/>+console_exec(session_id: str, code: str, mode: str='auto') Call[ExecResult]<br/>+console_names(session_id: str) Call[List of NameInfo]<br/>+console_close(session_id: str) Call[None]<br/>+custom_function(position: int, name: str, code: str, session_id: str?=None) Call[ExecResult]<br/>+dut_control_describe(position: int) Call[ApiTree]<br/>+dut_control_invoke(position: int, path: str, args: List[Any], kwargs: Dict[str,Any]) Call[InvokeRes]"]:::box
```

### Long-running work, instruments, and the plumbing

Sequence runs, chamber waits and ECA captures are activities: the start call returns an activity id and `activity.progress` / `activity.finished` events follow, routed by `ActivityTracker`. `Call` is the async result every port method returns.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    ActivityPort["<b>ActivityPort</b><hr/>+abort_activity(activity_id: str) Call"]:::box
    AutomationPort["<b>AutomationPort</b><hr/>+run_sequence(position: int, ops: List[Dict of str,Any], stop_on_error: bool=True) Call"]:::box
    InstrumentsPort["<b>InstrumentsPort</b><hr/>+list_instruments() Call[List of InstrumentFacts]<br/>+connect_instrument(instrument_id: str) Call[None]<br/>+siggen_get(instrument_id: str) Call[SiggenConfig]<br/>+siggen_set(instrument_id: str, config: SiggenConfig) Call[None]<br/>+siggen_waveforms(instrument_id: str, reload: bool=False) Call[List of str]<br/>+siggen_trigger(instrument_id: str, mode: str) Call[None]<br/>+siggen_rf(instrument_id: str, on: bool) Call[None]<br/>+chamber_read(instrument_id: str) Call[ChamberReading]<br/>+chamber_set_temp(instrument_id: str, celsius: float) Call[None]<br/>+chamber_wait_stable(instrument_id: str, tolerance_c: float=0.5, hold_s: float=60, timeout_s: float=3600) Call[str]<br/>+eca_sources(instrument_id: str) Call[EcaSources]<br/>+eca_capture(instrument_id: str, spec: CaptureSpec) Call[str]<br/>+eca_result(capture_id: str, offset: int=0, count: int=65536) Call[CapturePage]"]:::box
    Call["<b>Call</b><hr/>+succeeded(result: U=None) Call[U]<br/>+failed(error: ApiError) Call[Any]<br/>+pending bool<br/>+ok bool<br/>+result T?<br/>+error ApiError?<br/>+then(on_ok: Callable?=None, on_err: Callable?=None) Call[T]<br/>+resolve(result: T=None)<br/>+reject(error: ApiError)<br/>+map(fn: Callable) Call[U]"]:::box
    ActivityTracker["<b>ActivityTracker</b><hr/>+follow(activity_id: str, on_progress: Progress, on_done: Done)"]:::box
    AutomationPort -->|"extends"| ActivityPort
    InstrumentsPort -->|"extends"| ActivityPort
```

<details><summary>Constructors</summary>

```text
ActivityTracker(source: EventSource)
```

</details>

## 7. The fake station

`FakeStationGateway` implements `StationGateway` in memory, enforces the same requires rules as the real
service (`core/requires.py`) and returns the same error codes. It composes one part per area.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    FakeStationGateway["<b>FakeStationGateway</b><hr/>+set_latency(method: str, ms: int)<br/>+fail_next(method: str, code: ErrorCode, message: str='', data: Dict?=None)<br/>+time_out_next(method: str, late_ms: int=1500)<br/>+drop_dut(position: int, cause: str='RPC connection lost', detected_by: str='heartbeat')<br/>+drop_instrument(instrument_id: str)<br/>+release(count: int?=None)<br/>+emit_watch_tick(sub_id: str?=None)<br/>+calls_to(method: str) List[RecordedCall]<br/>+all StationGateway methods"]:::box
    AdvancedMethods["<b>AdvancedMethods</b><br/><i>«mixin»</i><hr/>+memory_* and console_*, custom_function, dut_control_* → self.advanced"]:::box
    FakeAdvanced["<b>FakeAdvanced</b><hr/>+sessions Dict[str,ConsoleSession]<br/>+duts Dict[int,FakeDut]<br/>+exec_time_limit_s float<br/>+dut(position: int) FakeDut<br/>+end_sessions(position: int)<br/>+run_op(position: int, kind: str, op: Dict) Any"]:::box
    FakeBench["<b>FakeBench</b><hr/>+instruments, siggen, chamber, ECA, RF switch state<br/>+require(kind: str, id: str?) InstrumentFacts<br/>+drop(id: str)<br/>+abort(activity_id: str) bool"]:::box
    FakeSequencer["<b>FakeSequencer</b><hr/>+start(activity: FakeActivity)<br/>+abort(activity_id: str)"]:::box
    RegisterMemory["<b>RegisterMemory</b><hr/>+read(name: str) int<br/>+write(name: str, value: int) int<br/>+field_insert(name: str, field: str, value: int) int"]:::box
    FakeMemory["<b>FakeMemory</b><hr/>+read(address: int, size: int) Tuple[int,bytes]<br/>+write(address: int, value: int, size: int) int"]:::box
    FakeDut["<b>FakeDut</b><hr/>+dut_control, rpc_io, rm, rta<br/>+method(path: str) Callable?"]:::box
    FakeStationGateway -->|"extends"| AdvancedMethods
    FakeStationGateway -->|"owns advanced"| FakeAdvanced
    FakeStationGateway -->|"owns bench"| FakeBench
    FakeStationGateway -->|"owns sequencer"| FakeSequencer
    FakeStationGateway -->|"owns memory"| RegisterMemory
    FakeAdvanced -->|"owns ram"| FakeMemory
    FakeAdvanced -->|"owns duts"| FakeDut
    FakeMemory -->|"peripheral window"| RegisterMemory
```

<details><summary>Constructors</summary>

```text
FakeStationGateway(scheduler: Scheduler?=None, peripherals: List[PeripheralDef]?=None, seed: int=7, clock: Callable=time.time)
FakeAdvanced(respond: Respond, log: Log, host: AdvancedHost, peripherals: List[PeripheralDef], seed: int)
FakeBench(scheduler: Scheduler, emit: Callable, log: Callable, emit_status: Callable, clock: Callable, chip: Callable)
```

</details>

## 8. Shared state

Four small stores, each with its own change event, so a status message doesn't refresh pages that only care about the DUT. `Event` is the plain-Python signal the services and stores use (Qt-free).

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    StationState["<b>StationState</b><hr/>+facts PositionFacts<br/>+connected bool<br/>+chip ChipInfo?<br/>+apply_status(status: StationStatus)<br/>+set_chip(position: int, chip: ChipInfo?)<br/>+set_connecting(connecting: bool)<br/>+set_position(position: int)<br/>+mark_disconnected(position: int, cause: str, detected_by: str)<br/>+facts_for(position: int) PositionFacts<br/>+missing(method: str, instrument_id: str?=None) List[str]<br/>+can(method: str, instrument_id: str?=None) bool<br/>+instrument(kind: str) InstrumentFacts?"]:::box
    SelectionState["<b>SelectionState</b><hr/>+select(selection: Selection, by_user: bool=True)<br/>+register RegisterDef?"]:::box
    PreferencesState["<b>PreferencesState</b><hr/>+update(**changes)"]:::box
    StatusLine["<b>StatusLine</b><hr/>+set(text: str)"]:::box
    Event["<b>Event</b><hr/>+connect(callback: Callable) Callable<br/>+disconnect(callback: Callable)<br/>+emit(*args)"]:::box
    StationState -.->|"changed, disconnected, position_changed"| Event
    SelectionState -.->|"changed"| Event
    PreferencesState -.->|"changed"| Event
    StatusLine -.->|"changed"| Event
```

<details><summary>Constructors</summary>

```text
StationState(position: int=1, backend_label: str='')
PreferencesState(preferences: Preferences?=None)
StatusLine(text: str='Ready')
```

</details>

## 9. Shell: pages, navigation, Ctrl+K

`domains/shell/pages.py` holds the page table (key, title, icon, QML file). `with_children()` turns every registered ViewModel into a constant `app.<name>` property. `app/commands.py` builds the Ctrl+K list.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    ServiceContainer["<b>ServiceContainer</b><hr/>+stop()<br/>+reload_user_data()<br/>+report_settings_problems()<br/>+start(autoconnect: bool=False, position: int=1)"]:::box
    ShellViewModel["<b>ShellViewModel</b><hr/>+pageSource(key: str) str<br/>+navigate(key: str)<br/>+child(name: str) QObject<br/>+2 bindable properties"]:::box
    StateViewModel["<b>StateViewModel</b><hr/>+setPosition(position: int)<br/>+toggleDarkMode()<br/>+12 bindable properties"]:::box
    CommandPaletteViewModel["<b>CommandPaletteViewModel</b><hr/>+open()<br/>+close()<br/>+setQuery(text: str)<br/>+move(delta: int)<br/>+trigger(kind: str, key: str)<br/>+activateCurrent()<br/>+activate(row: int)<br/>+7 bindable properties"]:::box
    DockViewModel["<b>DockViewModel</b><hr/>+setPage(key: str)<br/>+toggle()<br/>+show()<br/>+6 bindable properties"]:::box
    WindowsViewModel["<b>WindowsViewModel</b><hr/>+open(kind: str, arg: str='')<br/>+close(key: str)<br/>+show(key: str)<br/>+isOpen(kind: str, arg: str='') bool<br/>+keyFor(kind: str, arg: str='') str<br/>+closeAll()<br/>+open_keys() List[str]<br/>+2 bindable properties"]:::box
    pages_py["<b>pages_py</b><br/><i>«module domains/shell/pages.py»</i><hr/>+PAGES List[Dict]<br/>+page_source(key: str) str"]:::box
    commands_py["<b>commands_py</b><br/><i>«module app/commands.py»</i><hr/>+palette_commands(go, connection, state, detail, tree, actions, watch, dock, dumps, advanced, sessions) List[Command]"]:::box
    ServiceContainer -.->|"with_children(children)"| ShellViewModel
    ServiceContainer -.-> commands_py
    ShellViewModel -.-> pages_py
    ShellViewModel -->|"has"| StateViewModel
    ShellViewModel -->|"has"| CommandPaletteViewModel
    ShellViewModel -->|"has"| DockViewModel
    ShellViewModel -->|"has"| WindowsViewModel
```

<details><summary>Constructors</summary>

```text
ServiceContainer(gateway: StationGateway, home: Path, scheduler: Scheduler, backend_label: str='', interactions: InteractionService?=None, dumps_dir: Path?=None)
ShellViewModel(children: Dict~str,QObject~)
StateViewModel(state: StationState, prefs: PreferencesState, status: StatusLine)
CommandPaletteViewModel(selection: SelectionState, catalog: RegisterCatalog, actions: ActionService, sequences: SequenceService, navigate: Callable, select_action: Callable, select_sequence: Callable, commands: List~Command~)
DockViewModel(history: HistoryLog, log: LogService, actions: ActionService)
```

</details>

## 10. Registers page

Tree and favorites select a register (`SelectionState`); the detail panel shows and edits it; the shortcuts ViewModel sends it elsewhere (favorites, watch, logger, formulas, Actions).

### Registers page: services

Constructor arrows between services.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    RegisterCatalog["<b>RegisterCatalog</b><hr/>+load(position: int) Call<br/>+clear()<br/>+peripheral(name: str) PeripheralDef?<br/>+register(full_name: str) RegisterDef?<br/>+resolve(full_name: str) Tuple[RegisterDef?,FieldDef?]<br/>+search(text: str) SearchResult"]:::box
    RegisterService["<b>RegisterService</b><hr/>+cached(full_name: str) int?<br/>+previous_value(full_name: str) int?<br/>+clear_cache()<br/>+read(reg: RegisterDef, manual: bool=True, quiet: bool=False) Call<br/>+write(reg: RegisterDef, value: int) Call<br/>+write_field(reg: RegisterDef, field: FieldDef, value: int) Call<br/>+toggle_bit(reg: RegisterDef, bit: int) Call"]:::box
    ReadAllService["<b>ReadAllService</b><hr/>+running bool<br/>+start(periph: PeripheralDef) bool<br/>+cancel()"]:::box
    AnnotationService["<b>AnnotationService</b><hr/>+reload()<br/>+replace(notes: Dict[str,str], formulas: Dict[str,Tuple of str,str])<br/>+note(full_name: str) str<br/>+set_note(full_name: str, text: str)<br/>+formula(full_name: str) Tuple[str,str]?<br/>+set_formula(full_name: str, expr: str, unit: str='')<br/>+calculate(full_name: str, raw: int) float?<br/>+format_calculated(full_name: str, raw: int?) str"]:::box
    FavoritesService["<b>FavoritesService</b><hr/>+reload()<br/>+replace(names: List[str])<br/>+is_favorite(full_name: str) bool<br/>+toggle(full_name: str) bool<br/>+remove(full_name: str)"]:::box
    HistoryLog["<b>HistoryLog</b><hr/>+clock Callable<br/>+entries List[HistoryEntry]<br/>+record(operation: str, register: str, value: int, field_name: str?=None, register_value: int?=None) HistoryEntry<br/>+clear()<br/>+to_records() List[Dict of str,Any]<br/>+restore(records: List[Dict of str,Any])<br/>+by_ids(ids) List[HistoryEntry]<br/>+as_text() str"]:::box
    RegisterService -->|"history"| HistoryLog
    ReadAllService -->|"registers"| RegisterService
```

<details><summary>Constructors</summary>

```text
RegisterCatalog(gateway: RegistersPort, prefs: PreferencesState)
RegisterService(gateway: RegistersPort, state: StationState, prefs: PreferencesState, status: StatusLine, history: HistoryLog, interactions: InteractionService, errors: ErrorPresenter, log: LogService)
ReadAllService(registers: RegisterService, log: LogService)
AnnotationService(notes_store: JsonStore, formulas_store: JsonStore)
FavoritesService(store: JsonStore)
```

</details>

### Registers page: ViewModels

Slots QML calls; the services they use are shown by name (members above).

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    PeripheralTreeViewModel["<b>PeripheralTreeViewModel</b><hr/>+setSearchText(text: str)<br/>+requestSearchFocus()<br/>+flushSearch()<br/>+activate(row: int)<br/>+toggleExpanded(row: int)<br/>+collapseAll()<br/>+readAll(row: int)<br/>+3 bindable properties"]:::box
    FavoritesViewModel["<b>FavoritesViewModel</b><hr/>+activate(row: int)<br/>+remove(row: int)<br/>+2 bindable properties"]:::box
    RegisterDetailViewModel["<b>RegisterDetailViewModel</b><hr/>+read()<br/>+write(text: str)<br/>+toggleBit(bit: int)<br/>+setFormatIndex(index: int)<br/>+setFieldValue(row: int, text: str)<br/>+setNote(row: int, text: str)<br/>+21 bindable properties"]:::box
    RegisterShortcutsViewModel["<b>RegisterShortcutsViewModel</b><hr/>+toggleFavorite()<br/>+addToWatch(field: str)<br/>+addToLogger(field: str)<br/>+editFormula(field: str)<br/>+readPeripheral()<br/>+saveToActions()"]:::box
    ReadAllViewModel["<b>ReadAllViewModel</b><hr/>+cancel()<br/>+5 bindable properties"]:::box
    HistoryViewModel["<b>HistoryViewModel</b><hr/>+toggleReads()<br/>+toggleWrites()<br/>+select(row: int, mode: str)<br/>+runSelected()<br/>+createAction()<br/>+saveSelected()<br/>+generateCode()<br/>+copyAll()<br/>+clear()<br/>+4 bindable properties"]:::box
    FormulaEditorViewModel["<b>FormulaEditorViewModel</b><hr/>+open_for(field_full_name: str)<br/>+setExpr(text: str)<br/>+setUnit(text: str)<br/>+useExample(index: int)<br/>+test()<br/>+save()<br/>+remove()<br/>+cancel()<br/>+8 bindable properties"]:::box
    RegisterCatalog["<b>RegisterCatalog</b>"]:::stub
    RegisterService["<b>RegisterService</b>"]:::stub
    ReadAllService["<b>ReadAllService</b>"]:::stub
    FavoritesService["<b>FavoritesService</b>"]:::stub
    AnnotationService["<b>AnnotationService</b>"]:::stub
    HistoryLog["<b>HistoryLog</b>"]:::stub
    PeripheralTreeViewModel -->|"catalog"| RegisterCatalog
    PeripheralTreeViewModel -->|"registers"| RegisterService
    PeripheralTreeViewModel -->|"read_all"| ReadAllService
    FavoritesViewModel -->|"catalog"| RegisterCatalog
    FavoritesViewModel -->|"favorites"| FavoritesService
    RegisterDetailViewModel -->|"registers"| RegisterService
    RegisterDetailViewModel -->|"favorites"| FavoritesService
    RegisterDetailViewModel -->|"annotations"| AnnotationService
    RegisterShortcutsViewModel -->|"registers"| RegisterService
    RegisterShortcutsViewModel -->|"favorites"| FavoritesService
    RegisterShortcutsViewModel -->|"formula_editor"| FormulaEditorViewModel
    RegisterShortcutsViewModel -->|"read_all"| ReadAllService
    ReadAllViewModel -->|"service"| ReadAllService
    HistoryViewModel -->|"history"| HistoryLog
    HistoryViewModel -->|"catalog"| RegisterCatalog
    HistoryViewModel -->|"registers"| RegisterService
    FormulaEditorViewModel -->|"annotations"| AnnotationService
    RegisterShortcutsViewModel -->|"formula_editor"| FormulaEditorViewModel
    PeripheralTreeViewModel ~~~ RegisterShortcutsViewModel
    FavoritesViewModel ~~~ ReadAllViewModel
    RegisterDetailViewModel ~~~ HistoryViewModel
    RegisterShortcutsViewModel ~~~ FormulaEditorViewModel
```

<details><summary>Constructors</summary>

```text
PeripheralTreeViewModel(state: StationState, selection: SelectionState, prefs: PreferencesState, catalog: RegisterCatalog, registers: RegisterService, read_all: ReadAllService)
FavoritesViewModel(state: StationState, selection: SelectionState, catalog: RegisterCatalog, favorites: FavoritesService)
RegisterDetailViewModel(state: StationState, selection: SelectionState, prefs: PreferencesState, registers: RegisterService, favorites: FavoritesService, annotations: AnnotationService, interactions: InteractionService, runs_finished: Event)
RegisterShortcutsViewModel(selection: SelectionState, registers: RegisterService, favorites: FavoritesService, watch: WatchService, logger: DataLoggerService, actions: ActionRecorder, formula_editor: FormulaEditorViewModel, read_all: ReadAllService, interactions: InteractionService)
ReadAllViewModel(service: ReadAllService, interactions: InteractionService)
HistoryViewModel(history: HistoryLog, catalog: RegisterCatalog, registers: RegisterService, actions: ActionRecorder, interactions: InteractionService)
FormulaEditorViewModel(annotations: AnnotationService, interactions: InteractionService)
```

</details>

## 11. Watch and logger

Both use a `WatchSubscription` (registers.watch / registers.unwatch); values arrive as `WatchValues` events.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    WatchService["<b>WatchService</b><hr/>+reload()<br/>+live bool<br/>+add(full_name: str) bool<br/>+remove(full_name: str)<br/>+clear()<br/>+set_interval(interval_s: float)<br/>+start(interval_s: float?=None) Call<br/>+stop()<br/>+refresh_once() Call<br/>+write(full_name: str, value: int) Call"]:::box
    DataLoggerService["<b>DataLoggerService</b><hr/>+reload()<br/>+recording bool<br/>+mode str<br/>+elapsed_s float<br/>+track(full_name: str) bool<br/>+untrack(full_name: str)<br/>+set_rate(rate_s: float)<br/>+start(rate_s: float?=None) Call<br/>+stop()<br/>+clear()<br/>+export_csv(path: Path) Path"]:::box
    WatchSubscription["<b>WatchSubscription</b><hr/>+active bool<br/>+start(registers: List[str], interval_s: float, context: str) Call<br/>+stop()<br/>+forget()"]:::box
    WatchListViewModel["<b>WatchListViewModel</b><hr/>+setLarge(large: bool)<br/>+setIntervalText(text: str)<br/>+toggleLive()<br/>+refreshOnce()<br/>+select(row: int, mode: str)<br/>+writeValue(row: int)<br/>+remove(row: int)<br/>+removeSelected()<br/>+clearAll()<br/>+addAllToLogger()<br/>+addSelectedToLogger()<br/>+addRowToLogger(row: int)<br/>+5 bindable properties"]:::box
    DataLoggerViewModel["<b>DataLoggerViewModel</b><hr/>+toggleRecording()<br/>+setRateText(text: str)<br/>+remove(row: int)<br/>+clear()<br/>+zoomTo(start: float, end: float)<br/>+resetZoom()<br/>+exportCsv()<br/>+9 bindable properties"]:::box
    WatchListViewModel -->|"watch"| WatchService
    WatchListViewModel -->|"logger"| DataLoggerService
    DataLoggerViewModel -->|"logger"| DataLoggerService
    WatchService -->|"owns _sub"| WatchSubscription
    DataLoggerService -->|"owns _sub"| WatchSubscription
```

<details><summary>Constructors</summary>

```text
WatchService(gateway: RegistersPort, state: StationState, catalog: RegisterCatalog, registers: RegisterService, store: JsonStore, errors: ErrorPresenter, clock: Callable=time.time)
DataLoggerService(gateway: RegistersPort, state: StationState, catalog: RegisterCatalog, annotations: AnnotationService, store: JsonStore, errors: ErrorPresenter, scheduler: Scheduler, clock: Callable=time.time)
WatchSubscription(gateway: RegistersPort, state: StationState, errors: ErrorPresenter)
WatchListViewModel(watch: WatchService, logger: DataLoggerService, annotations: AnnotationService, interactions: InteractionService, prefs: PreferencesState)
DataLoggerViewModel(logger: DataLoggerService, interactions: InteractionService, export_dir: Path)
```

</details>

## 12. Actions and sequences

Every operation kind is one `OpKind` in `core/ops.py` (`KINDS`), used by `describe_op(op)`, `code_lines(op, functions)` (code generation) and `to_wire(op, functions)` (automation.seq.run). Pages that offer Add to Actions depend on `ActionRecorder`.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    ActionService["<b>ActionService</b><hr/>+reload()<br/>+replace(raw: Dict[str,Any])<br/>+get(name: str) Action?<br/>+unique_name(name: str) str<br/>+add(name: str, ops: List[Dict of str,Any], enabled: bool=True) Action<br/>+update(name: str, ops: List[Dict of str,Any])<br/>+deselect_all()<br/>+remove(name: str)<br/>+remove_all()<br/>+set_enabled(name: str, enabled: bool)<br/>+move(name: str, delta: int)<br/>+wire_ops(name: str) List[Dict of str,Any]<br/>+ops_for(names: List[str]) List[Dict of str,Any]<br/>+run(names: List[str]) Call<br/>+run_enabled() Call<br/>+generate_code(names: List[str]) str"]:::box
    SequenceService["<b>SequenceService</b><hr/>+reload()<br/>+description(name: str) str<br/>+create(name: str, action_names: List[str]) str<br/>+rename(old: str, new: str) str<br/>+add_steps(name: str, action_names: List[str])<br/>+to_action(name: str) str<br/>+delete(name: str)<br/>+move_step(name: str, index: int, delta: int)<br/>+remove_step(name: str, index: int)<br/>+plan(name: str, wire: bool=False) Tuple[List of Step,List of Dict of str,Any]<br/>+preview(name: str) List[Step]<br/>+run(name: str) Call<br/>+abort()<br/>+generate_code(name: str) str"]:::box
    ActionRecorder["<b>ActionRecorder</b><hr/>+add(name: str, ops: List[Dict of str,Any], enabled: bool=True) Action"]:::box
    ActivityTracker["<b>ActivityTracker</b><hr/>+follow(activity_id: str, on_progress: Progress, on_done: Done)"]:::box
    OpKind["<b>OpKind</b><hr/>+name str<br/>+describe Callable<br/>+code Callable<br/>+wire_fields Tuple[str,...]?<br/>+to_wire Callable?<br/>+carries_code bool<br/>+editable bool<br/>+wire(op: Op, functions: Functions) Op"]:::box
    ActionsViewModel["<b>ActionsViewModel</b><hr/>+select(row: int)<br/>+select_name(name: str)<br/>+toggleEnabled(row: int)<br/>+deselectAll()<br/>+runCurrent()<br/>+runSelected()<br/>+viewCurrent()<br/>+editCurrent()<br/>+moveCurrent(delta: int)<br/>+removeCurrent()<br/>+removeAll()<br/>+addCheckedToSequence()<br/>+generateCode()<br/>+4 bindable properties"]:::box
    SequencesViewModel["<b>SequencesViewModel</b><hr/>+select(row: int)<br/>+select_name(name: str)<br/>+selectStep(row: int)<br/>+run()<br/>+abort()<br/>+newSequence()<br/>+renameSequence()<br/>+deleteSequence()<br/>+addToActions()<br/>+addAction()<br/>+removeSelectedStep()<br/>+moveSelectedStep(delta: int)<br/>+generateCode()<br/>+10 bindable properties"]:::box
    ActionEditorViewModel["<b>ActionEditorViewModel</b><hr/>+open_view(name: str)<br/>+closeView()<br/>+open_edit(name: str)<br/>+setEditValue(row: int, text: str)<br/>+saveEdit()<br/>+cancelEdit()<br/>+6 bindable properties"]:::box
    ops_py["<b>ops_py</b><br/><i>«module core/ops.py»</i><hr/>+KINDS Dict[str,OpKind]<br/>+op_kind(op: Op) str<br/>+describe_op(op: Op) str<br/>+code_lines(op: Op, functions: Functions) List[str]<br/>+to_wire(op: Op, functions: Functions) Op<br/>+carries_code(kind: str) bool<br/>+editable(kind: str) bool"]:::box
    wire_ops_py["<b>wire_ops_py</b><br/><i>«module core/wire_ops.py»</i><hr/>+action_ops(action: Action, actions: Callable, custom_functions: Mapping) List[Dict]"]:::box
    ActionService -->|"activities"| ActivityTracker
    SequenceService -->|"actions"| ActionService
    SequenceService -->|"activities"| ActivityTracker
    ActionsViewModel -->|"actions"| ActionService
    ActionsViewModel -->|"sequences"| SequenceService
    ActionsViewModel -->|"editor"| ActionEditorViewModel
    SequencesViewModel -->|"sequences"| SequenceService
    SequencesViewModel -->|"actions"| ActionService
    ActionEditorViewModel -->|"actions"| ActionService
    ActionService -.->|"implements"| ActionRecorder
    ops_py -->|"has"| OpKind
    wire_ops_py -.-> ops_py
    ActionService -.-> wire_ops_py
    ActionEditorViewModel -.-> ops_py
```

<details><summary>Constructors</summary>

```text
ActionService(store: JsonStore, gateway: AutomationPort, state: StationState, activities: ActivityTracker, errors: ErrorPresenter, log: LogService, custom_functions: JsonStore?=None)
SequenceService(store: JsonStore, actions: ActionService, gateway: AutomationPort, state: StationState, activities: ActivityTracker, errors: ErrorPresenter, log: LogService, clock: Callable=time.time)
ActivityTracker(source: EventSource)
ActionsViewModel(actions: ActionService, sequences: SequenceService, editor: ActionEditorViewModel, state: StationState, interactions: InteractionService)
SequencesViewModel(sequences: SequenceService, actions: ActionService, state: StationState, interactions: InteractionService)
ActionEditorViewModel(actions: ActionService, catalog: RegisterCatalog, prefs: PreferencesState, interactions: InteractionService)
```

</details>

## 13. Dumps and Radio Calculator diff

`DumpsViewModel` starts the work; the picker, the progress dialog and the comparison card are separate ViewModels it drives.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    DumpService["<b>DumpService</b><hr/>+running bool<br/>+files() List[DumpFile]<br/>+save(dump: RegisterDump) Path<br/>+delete(path: Path)<br/>+compare_files(first: Path, second: Path) Comparison<br/>+take(peripherals: List[str], on_done: Callable) bool<br/>+diff_live(path: Path, on_done: Callable) bool<br/>+radio_diff(config: RadioConfig, peripherals: List[str], on_done: Callable) bool<br/>+cancel()<br/>+new_dump(job: DumpJob, name: str, description: str='') RegisterDump<br/>+to_records() List[Dict of str,Any]<br/>+restore(records: List[Dict of str,Any])"]:::box
    DumpsViewModel["<b>DumpsViewModel</b><hr/>+refresh()<br/>+select(row: int)<br/>+deleteSelected()<br/>+openPicker()<br/>+diffLive()<br/>+compareWith()<br/>+compareFiles()<br/>+openRadioDiff()<br/>+4 bindable properties"]:::box
    PeripheralPickerViewModel["<b>PeripheralPickerViewModel</b><hr/>+open(mode: str, wording: tuple, checked: Dict[str,bool], label: Callable, on_start: Callable)<br/>+checked() Dict[str,bool]<br/>+closePicker()<br/>+togglePeripheral(row: int)<br/>+selectAll()<br/>+selectNone()<br/>+startPicked()<br/>+7 bindable properties"]:::box
    DumpProgressViewModel["<b>DumpProgressViewModel</b><hr/>+begin(title: str)<br/>+cancel()<br/>+6 bindable properties"]:::box
    ComparisonViewModel["<b>ComparisonViewModel</b><hr/>+show(result: Comparison)<br/>+show_radio(result: RadioComparison)<br/>+sortBy(column: str)<br/>+clearResult()<br/>+saveReport()<br/>+14 bindable properties"]:::box
    DumpsViewModel -->|"service"| DumpService
    DumpsViewModel -->|"picker"| PeripheralPickerViewModel
    DumpsViewModel -->|"progress"| DumpProgressViewModel
    DumpsViewModel -->|"comparison"| ComparisonViewModel
    DumpProgressViewModel -->|"service"| DumpService
```

<details><summary>Constructors</summary>

```text
DumpService(directory: Path, catalog: RegisterCatalog, registers: RegisterService, log: LogService, clock: Callable=…)
DumpsViewModel(service: DumpService, catalog: RegisterCatalog, state: StationState, prefs: PreferencesState, interactions: InteractionService, picker: PeripheralPickerViewModel, progress: DumpProgressViewModel, comparison: ComparisonViewModel)
DumpProgressViewModel(service: DumpService)
ComparisonViewModel(reports_dir: Path, interactions: InteractionService)
```

</details>

## 14. Radio and PHY

PHY loading goes through `ConnectionService.load_phy` (dut.load_phy); PRS routing through `RfPort`.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    PhyService["<b>PhyService</b><hr/>+can_load bool<br/>+wifi_supported bool<br/>+chip_family str<br/>+load_lpw(name: str) Call[LoadPhyResult]<br/>+load_wifi(config: WifiPhyConfig) Call[LoadPhyResult]<br/>+add_lpw_action(name: str) Action<br/>+add_wifi_action(config: WifiPhyConfig) Action"]:::box
    PrsService["<b>PrsService</b><hr/>+source_text str<br/>+load_signals() Call[PrsSignalCatalog]<br/>+problem(route: PrsRoute) str?<br/>+apply(route: PrsRoute) Call[None]<br/>+remove(route: PrsRoute) Call[None]<br/>+add_action(route: PrsRoute) Action"]:::box
    LpwPhyViewModel["<b>LpwPhyViewModel</b><hr/>+setPhyName(name: str)<br/>+browse()<br/>+load()<br/>+addToActions()<br/>+5 bindable properties"]:::box
    WifiPhyViewModel["<b>WifiPhyViewModel</b><hr/>+setMode(mode: str)<br/>+setStandard(standard: str)<br/>+setChannel(channel: str)<br/>+setPowerMode(power_mode: str)<br/>+setRate(rate: str)<br/>+setPktLength(text: str)<br/>+setNumPkts(text: str)<br/>+setTransmitMode(mode: str)<br/>+setAggrEnable(on: bool)<br/>+setAdvancedEnabled(on: bool)<br/>+setPpduType(ppdu: str)<br/>+setGiLtf(gi_ltf: str)<br/>+setDcm(on: bool)<br/>+setBandwidth(bandwidth: str)<br/>+apply()<br/>+addToActions()<br/>+closeResult()<br/>+settings() WifiSettings<br/>+35 bindable properties"]:::box
    PrsViewModel["<b>PrsViewModel</b><hr/>+setSignal(index: int)<br/>+setPin(index: int)<br/>+setChannel(index: int)<br/>+apply()<br/>+remove(row: int)<br/>+addToActions()<br/>+current_route() PrsRoute<br/>+13 bindable properties"]:::box
    LpwPhyViewModel -->|"service"| PhyService
    WifiPhyViewModel -->|"service"| PhyService
    PrsViewModel -->|"service"| PrsService
```

<details><summary>Constructors</summary>

```text
PhyService(connection: ConnectionService, state: StationState, actions: ActionRecorder)
PrsService(gateway: RfPort, state: StationState, history: HistoryLog, actions: ActionRecorder, errors: ErrorPresenter, log: LogService)
LpwPhyViewModel(service: PhyService, state: StationState, interactions: InteractionService)
WifiPhyViewModel(service: PhyService, state: StationState, interactions: InteractionService)
PrsViewModel(service: PrsService, state: StationState, interactions: InteractionService)
```

</details>

## 15. Instruments

`InstrumentBench` finds the instrument of each kind in `StationState.instruments` and follows instrument activities (chamber waits, ECA captures) through the shared `ActivityTracker`.

### Instruments: services

Constructor arrows between services.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    InstrumentBench["<b>InstrumentBench</b><hr/>+instrument(kind: str) InstrumentFacts?<br/>+instrument_id(kind: str) str<br/>+describe(kind: str) str<br/>+connect(kind: str) Call[None]<br/>+follow(activity_id: str, on_progress: Progress, on_done: Done)<br/>+abort(activity_id: str) Call[Any]"]:::box
    SignalGeneratorService["<b>SignalGeneratorService</b><hr/>+instrument_id str<br/>+can(method: str) bool<br/>+reload()<br/>+remember(settings: SiggenSettings)<br/>+load_waveforms(reload: bool=False) Call[List of str]<br/>+apply(settings: SiggenSettings) Call[None]<br/>+load_from_instrument() Call[SiggenConfig]<br/>+trigger(mode: str) Call[None]<br/>+set_rf(on: bool) Call[None]<br/>+add_action(settings: SiggenSettings) Action"]:::box
    RfSwitchService["<b>RfSwitchService</b><hr/>+current_path(position: int) str<br/>+load_paths() Call[List of str]<br/>+connect(position: int, path: str) Call[None]<br/>+disconnect(position: int) Call[None]<br/>+add_action(path: str, position: int) Action"]:::box
    ChamberService["<b>ChamberService</b><hr/>+instrument_id str<br/>+can(method: str) bool<br/>+start_polling(interval_s: float?=None)<br/>+stop_polling()<br/>+polling bool<br/>+read() Call[ChamberReading]<br/>+set_temperature(celsius: float) Call[None]<br/>+wait_stable(tolerance_c: float, hold_s: float) Call[str]<br/>+abort_wait()"]:::box
    EcaService["<b>EcaService</b><hr/>+instrument_id str<br/>+can(method: str) bool<br/>+busy bool<br/>+load_sources() Call[EcaSources]<br/>+start(spec: CaptureSpec) Call[str]<br/>+abort()<br/>+save_csv(path: Path)"]:::box
    PacketService["<b>PacketService</b><hr/>+reload()<br/>+remember_ble(packet: BlePacket)<br/>+siggen_id str<br/>+add_gfsk_action(packet: GfskPacket) Action"]:::box
    SignalGeneratorService -->|"bench"| InstrumentBench
    RfSwitchService -->|"bench"| InstrumentBench
    ChamberService -->|"bench"| InstrumentBench
    EcaService -->|"bench"| InstrumentBench
```

<details><summary>Constructors</summary>

```text
InstrumentBench(gateway: InstrumentsPort, state: StationState, activities: ActivityTracker, errors: ErrorPresenter, log: LogService)
SignalGeneratorService(gateway: InstrumentsPort, state: StationState, bench: InstrumentBench, store: JsonStore, actions: ActionRecorder, errors: ErrorPresenter, log: LogService)
RfSwitchService(gateway: RfPort, state: StationState, bench: InstrumentBench, actions: ActionRecorder, errors: ErrorPresenter, log: LogService)
ChamberService(gateway: InstrumentsPort, state: StationState, bench: InstrumentBench, errors: ErrorPresenter, log: LogService, scheduler: Scheduler)
EcaService(gateway: InstrumentsPort, state: StationState, bench: InstrumentBench, errors: ErrorPresenter, log: LogService)
PacketService(store: JsonStore, actions: ActionRecorder, siggen_id: Callable)
```

</details>

### Instruments: ViewModels

Slots QML calls; the services they use are shown by name (members above).

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    InstrumentViewModel["<b>InstrumentViewModel</b><hr/>+connectInstrument()"]:::box
    SignalGeneratorViewModel["<b>SignalGeneratorViewModel</b><hr/>+setField(name: str, value: str)<br/>+setWaveform(index: int)<br/>+apply()<br/>+loadFromInstrument()<br/>+reloadWaveforms()<br/>+trigger(mode: str)<br/>+setRf(on: bool)<br/>+addToActions()<br/>+showCode()<br/>+14 bindable properties"]:::box
    RfSwitchViewModel["<b>RfSwitchViewModel</b><hr/>+setPath(index: int)<br/>+setPosition(index: int)<br/>+connectPath()<br/>+disconnectPath()<br/>+addToActions()<br/>+9 bindable properties"]:::box
    ChamberViewModel["<b>ChamberViewModel</b><hr/>+setField(name: str, value: str)<br/>+setActive(active: bool)<br/>+setTemperature()<br/>+waitForStable()<br/>+abortWait()<br/>+13 bindable properties"]:::box
    EcaViewModel["<b>EcaViewModel</b><hr/>+setField(name: str, value: str)<br/>+toggleChannel(row: int)<br/>+setTrigger(index: int)<br/>+setEdge(index: int)<br/>+spec() CaptureSpec<br/>+capture()<br/>+abort()<br/>+zoom(start: float, end: float)<br/>+resetZoom()<br/>+saveCsv()<br/>+22 bindable properties"]:::box
    BlePacketViewModel["<b>BlePacketViewModel</b><hr/>+setField(name: str, value: str)<br/>+generateCode()<br/>+8 bindable properties"]:::box
    GfskPacketViewModel["<b>GfskPacketViewModel</b><hr/>+setField(name: str, value: str)<br/>+setPayload(index: int)<br/>+generateCode()<br/>+addToActions()<br/>+12 bindable properties"]:::box
    InstrumentBench["<b>InstrumentBench</b>"]:::stub
    SignalGeneratorService["<b>SignalGeneratorService</b>"]:::stub
    RfSwitchService["<b>RfSwitchService</b>"]:::stub
    ChamberService["<b>ChamberService</b>"]:::stub
    EcaService["<b>EcaService</b>"]:::stub
    PacketService["<b>PacketService</b>"]:::stub
    InstrumentViewModel -->|"bench"| InstrumentBench
    SignalGeneratorViewModel -->|"service"| SignalGeneratorService
    SignalGeneratorViewModel -->|"bench"| InstrumentBench
    RfSwitchViewModel -->|"service"| RfSwitchService
    RfSwitchViewModel -->|"bench"| InstrumentBench
    ChamberViewModel -->|"service"| ChamberService
    ChamberViewModel -->|"bench"| InstrumentBench
    EcaViewModel -->|"service"| EcaService
    EcaViewModel -->|"bench"| InstrumentBench
    BlePacketViewModel -->|"service"| PacketService
    GfskPacketViewModel -->|"service"| PacketService
    SignalGeneratorViewModel -->|"extends"| InstrumentViewModel
    RfSwitchViewModel -->|"extends"| InstrumentViewModel
    ChamberViewModel -->|"extends"| InstrumentViewModel
    EcaViewModel -->|"extends"| InstrumentViewModel
    InstrumentViewModel ~~~ ChamberViewModel
    SignalGeneratorViewModel ~~~ EcaViewModel
    RfSwitchViewModel ~~~ BlePacketViewModel
    ChamberViewModel ~~~ GfskPacketViewModel
```

<details><summary>Constructors</summary>

```text
InstrumentViewModel(bench: InstrumentBench, state: StationState)
SignalGeneratorViewModel(service: SignalGeneratorService, bench: InstrumentBench, state: StationState, interactions: InteractionService)
RfSwitchViewModel(service: RfSwitchService, bench: InstrumentBench, state: StationState, interactions: InteractionService)
ChamberViewModel(service: ChamberService, bench: InstrumentBench, state: StationState, interactions: InteractionService)
EcaViewModel(service: EcaService, bench: InstrumentBench, state: StationState, interactions: InteractionService)
BlePacketViewModel(service: PacketService, interactions: InteractionService)
GfskPacketViewModel(service: PacketService, interactions: InteractionService)
```

</details>

## 16. Advanced

The console and custom functions share one station-side Python session per DUT (`PythonSession`).

### Advanced: services

Constructor arrows between services.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    PythonSession["<b>PythonSession</b><hr/>+open bool<br/>+ensure() Call[str]<br/>+with_session(run: Callable) Call[T]<br/>+restart()"]:::box
    ConsoleService["<b>ConsoleService</b><hr/>+run(code: str)<br/>+show_help()<br/>+restart()"]:::box
    CustomFunctionService["<b>CustomFunctionService</b><hr/>+reload()<br/>+names List[str]<br/>+code(name: str) str?<br/>+new_name() str<br/>+create(name: str) str<br/>+rename(old: str, new: str) str<br/>+delete(name: str)<br/>+set_code(name: str, code: str)<br/>+run(name: str)<br/>+add_to_actions(name: str) Action"]:::box
    DutControlService["<b>DutControlService</b><hr/>+load(force: bool=False)<br/>+method(path: str) ApiMethod?<br/>+invoke(path: str, kwargs: Dict[str,Any])<br/>+add_to_actions(path: str, kwargs: Dict[str,Any]) Action"]:::box
    MemoryService["<b>MemoryService</b><hr/>+last_address str<br/>+read(address: int, size: int) Call[MemoryBlock]<br/>+write(address: int, value: int, size: int) Call[MemoryWriteRes]<br/>+reload()"]:::box
    OutputLog["<b>OutputLog</b><hr/>+add(lines: Iterable[Line])<br/>+line(level: str, text: str)<br/>+clear()<br/>+text() str"]:::box
    ConsoleService -->|"session"| PythonSession
    CustomFunctionService -->|"session"| PythonSession
    ConsoleService -->|"owns output"| OutputLog
    CustomFunctionService -->|"owns output"| OutputLog
    DutControlService -->|"owns output"| OutputLog
```

<details><summary>Constructors</summary>

```text
PythonSession(gateway: AdvancedPort, state: StationState)
ConsoleService(gateway: AdvancedPort, state: StationState, session: PythonSession, errors: ErrorPresenter)
CustomFunctionService(store: JsonStore, gateway: AdvancedPort, state: StationState, session: PythonSession, actions: ActionRecorder, errors: ErrorPresenter)
DutControlService(gateway: AdvancedPort, state: StationState, actions: ActionRecorder, errors: ErrorPresenter)
MemoryService(gateway: MemoryPort, state: StationState, store: JsonStore, errors: ErrorPresenter, log: LogService)
```

</details>

### Advanced: ViewModels

Slots QML calls; the services they use are shown by name (members above).

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    AdvancedViewModel["<b>AdvancedViewModel</b><hr/>+setTab(index: int)<br/>+show(name: str)<br/>+2 bindable properties"]:::box
    ConsoleViewModel["<b>ConsoleViewModel</b><hr/>+setDraft(text: str)<br/>+execute()<br/>+historyPrevious()<br/>+historyNext()<br/>+help()<br/>+restart()<br/>+5 bindable properties"]:::box
    CustomFunctionsViewModel["<b>CustomFunctionsViewModel</b><hr/>+select(index: int)<br/>+setCode(text: str)<br/>+attachHighlighter(document: QObject, dark: bool)<br/>+newFunction()<br/>+renameFunction()<br/>+deleteFunction()<br/>+run()<br/>+addToActions()<br/>+10 bindable properties"]:::box
    DutControlViewModel["<b>DutControlViewModel</b><hr/>+load()<br/>+reload()<br/>+setFilter(text: str)<br/>+activate(row: int)<br/>+collapseAll()<br/>+setParam(name: str, value: str)<br/>+execute()<br/>+addToActions()<br/>+13 bindable properties"]:::box
    MemoryViewModel["<b>MemoryViewModel</b><hr/>+setField(name: str, value: str)<br/>+setFormat(index: int)<br/>+setWriteSize(index: int)<br/>+read()<br/>+useRowAddress(row: int)<br/>+write()<br/>+copyDump()<br/>+18 bindable properties"]:::box
    ConsoleService["<b>ConsoleService</b>"]:::stub
    PythonSession["<b>PythonSession</b>"]:::stub
    CustomFunctionService["<b>CustomFunctionService</b>"]:::stub
    DutControlService["<b>DutControlService</b>"]:::stub
    MemoryService["<b>MemoryService</b>"]:::stub
    ConsoleViewModel -->|"service"| ConsoleService
    ConsoleViewModel -->|"session"| PythonSession
    CustomFunctionsViewModel -->|"service"| CustomFunctionService
    DutControlViewModel -->|"service"| DutControlService
    MemoryViewModel -->|"service"| MemoryService
    AdvancedViewModel ~~~ DutControlViewModel
    ConsoleViewModel ~~~ MemoryViewModel
```

<details><summary>Constructors</summary>

```text
ConsoleViewModel(service: ConsoleService, session: PythonSession, state: StationState)
CustomFunctionsViewModel(service: CustomFunctionService, state: StationState, interactions: InteractionService, highlighters: HighlighterHost)
DutControlViewModel(service: DutControlService, state: StationState, interactions: InteractionService)
MemoryViewModel(service: MemoryService, state: StationState, interactions: InteractionService)
```

</details>

## 17. Connection, settings, sessions, log

`ErrorPresenter` is how services report station failures: one log line and one toast.

### Connection, settings, sessions, log: services

Constructor arrows between services.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    ConnectionService["<b>ConnectionService</b><hr/>+start() Call<br/>+refresh_status() Call<br/>+connect(position: int, config_type: str='EFR32', config_file: str='', rpc: RpcAddress?=None) Call<br/>+reconnect(position: int) Call<br/>+dut_info() Call<br/>+recover(position: int) Call<br/>+disconnect(position: int) Call<br/>+load_phy(position: int, phy: PhySpec) Call[LoadPhyResult]"]:::box
    HardwareConfigService["<b>HardwareConfigService</b><hr/>+reload()<br/>+save(config: HardwareConfig) Call<br/>+test_connection(config: HardwareConfig) Call"]:::box
    SessionService["<b>SessionService</b><hr/>+snapshot(name: str, created: str?=None) Dict[str,Any]<br/>+apply(data: Dict[str,Any])<br/>+path_for(name: str) Path<br/>+exists(name: str) bool<br/>+list() List[SessionInfo]<br/>+save(name: str) SessionInfo<br/>+load(name: str) SessionInfo<br/>+delete(name: str)<br/>+preview(name: str) Dict[str,Any]<br/>+start_autosave(interval_ms: int=AUTOSAVE_MS)<br/>+stop_autosave()<br/>+autosave()<br/>+restore_autosave() int"]:::box
    SettingsTransfer["<b>SettingsTransfer</b><hr/>+export(path: Path) List[str]<br/>+import_(path: Path) Tuple[List of str,List of Problem]<br/>+clear_all()"]:::box
    ErrorPresenter["<b>ErrorPresenter</b><hr/>+message_for(error: ApiError) str<br/>+present(error: ApiError, context: str='')<br/>+verify_mismatch(target: str, written: int, readback: int)"]:::box
    LogService["<b>LogService</b><hr/>+add(level: str, text: str, source: str='ui')<br/>+debug(text: str)<br/>+info(text: str)<br/>+success(text: str)<br/>+warning(text: str)<br/>+error(text: str)<br/>+clear()<br/>+on_gateway_event(event: object)"]:::box
    ConnectionService -->|"errors"| ErrorPresenter
    ConnectionService -->|"log"| LogService
    HardwareConfigService -->|"log"| LogService
    SessionService -->|"log"| LogService
    ErrorPresenter -->|"log"| LogService
```

<details><summary>Constructors</summary>

```text
ConnectionService(gateway: ConnectionGateway, state: StationState, catalog: RegisterCatalog, errors: ErrorPresenter, log: LogService)
HardwareConfigService(store: JsonStore, gateway: DutPort, state: StationState, log: LogService)
SessionService(directory: Path, autosave_path: Path, annotations: AnnotationService, favorites: FavoritesService, actions: ActionService, history: HistoryLog, dumps: DumpService, log: LogService, scheduler: Scheduler, clock: Callable=…)
SettingsTransfer(stores: UserStores, reload_all: Callable)
ErrorPresenter(interactions: InteractionService, log: LogService)
LogService(clock: Callable=time.time)
```

</details>

### Connection, settings, sessions, log: ViewModels

Slots QML calls; the services they use are shown by name (members above).

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TB
    classDef box text-align:left,fill:#f8f8ff,stroke:#6a6ab0,color:#1c1c1c
    classDef stub fill:#ffffff,stroke:#6a6ab0,stroke-dasharray:4 3,color:#1c1c1c
    ConnectionViewModel["<b>ConnectionViewModel</b><hr/>+openSheet()<br/>+setOverride(on: bool)<br/>+setRpcHost(host: str)<br/>+setRpcPort(port: str)<br/>+closeSheet()<br/>+setPosition(position: int)<br/>+setConfigTypeIndex(index: int)<br/>+setConfigFile(path: str)<br/>+connect()<br/>+disconnectDut()<br/>+10 bindable properties"]:::box
    DisconnectRecoveryViewModel["<b>DisconnectRecoveryViewModel</b><hr/>+reconnect()<br/>+loadLpwPhy()<br/>+loadWifiPhy()<br/>+addReconnectToActions()<br/>+dismiss()<br/>+9 bindable properties"]:::box
    SystemInfoViewModel["<b>SystemInfoViewModel</b><hr/>+refresh()<br/>+setTabIndex(index: int)<br/>+copyAll()<br/>+text() str<br/>+6 bindable properties"]:::box
    SettingsViewModel["<b>SettingsViewModel</b><hr/>+setDarkMode(on: bool)<br/>+setAutoRead(on: bool)<br/>+setConfirmCritical(on: bool)<br/>+setShowSecure(on: bool)<br/>+clearRegisterCache()<br/>+exportSettings()<br/>+importSettings()<br/>+clearAllSettings()<br/>+5 bindable properties"]:::box
    HardwareConfigViewModel["<b>HardwareConfigViewModel</b><hr/>+setField(name: str, value: str)<br/>+setOverride(on: bool)<br/>+save()<br/>+testConnection()<br/>+10 bindable properties"]:::box
    SessionsViewModel["<b>SessionsViewModel</b><hr/>+saveSession()<br/>+openBrowser()<br/>+closeBrowser()<br/>+select(row: int)<br/>+loadSelected()<br/>+deleteSelected()<br/>+5 bindable properties"]:::box
    LogViewModel["<b>LogViewModel</b><hr/>+toggleLevel(index: int)<br/>+setSearchText(text: str)<br/>+nextMatch()<br/>+previousMatch()<br/>+saveLog()<br/>+clear()<br/>+setPoppedOut(on: bool)<br/>+6 bindable properties"]:::box
    ConnectionService["<b>ConnectionService</b>"]:::stub
    LogService["<b>LogService</b>"]:::stub
    HardwareConfigService["<b>HardwareConfigService</b>"]:::stub
    SettingsTransfer["<b>SettingsTransfer</b>"]:::stub
    SessionService["<b>SessionService</b>"]:::stub
    ConnectionViewModel -->|"service"| ConnectionService
    ConnectionViewModel -->|"log"| LogService
    ConnectionViewModel -->|"hardware"| HardwareConfigService
    DisconnectRecoveryViewModel -->|"service"| ConnectionService
    SystemInfoViewModel -->|"connection"| ConnectionService
    SettingsViewModel -->|"transfer"| SettingsTransfer
    HardwareConfigViewModel -->|"service"| HardwareConfigService
    SessionsViewModel -->|"service"| SessionService
    LogViewModel -->|"log"| LogService
    ConnectionViewModel ~~~ SettingsViewModel
    DisconnectRecoveryViewModel ~~~ HardwareConfigViewModel
    SystemInfoViewModel ~~~ SessionsViewModel
    SettingsViewModel ~~~ LogViewModel
```

<details><summary>Constructors</summary>

```text
ConnectionViewModel(service: ConnectionService, state: StationState, log: LogService, hardware: HardwareConfigService?=None, interactions: InteractionService?=None)
DisconnectRecoveryViewModel(service: ConnectionService, state: StationState, actions: ActionRecorder, interactions: InteractionService, open_radio_page: Callable=…)
SystemInfoViewModel(connection: ConnectionService, state: StationState, interactions: InteractionService)
SettingsViewModel(state: StationState, prefs: PreferencesState, on_clear_cache: Callable, transfer: SettingsTransfer, interactions: InteractionService)
HardwareConfigViewModel(service: HardwareConfigService)
SessionsViewModel(service: SessionService, interactions: InteractionService)
LogViewModel(log: LogService, interactions: InteractionService)
```

</details>

## 18. ViewModels to backend endpoints

What the real station service must answer for each screen to work. Solid arrows are calls a user action
triggers, traced from each ViewModel slot through the services to the gateway (`callgraph`, not hand-drawn).
47 endpoints in total; the ones marked
⚠ unused are in the API design but no screen calls them yet (instruments.list).

### Overview: pages to API areas

Arrow labels are how many endpoints of that area the page calls.

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    Registers["Registers"]
    Watch["Watch"]
    Actions_and_sequences["Actions and sequences"]
    Dumps["Dumps"]
    Radio["Radio"]
    Instruments["Instruments"]
    Advanced["Advanced"]
    Connection_and_settings["Connection and settings"]
    ns_sys[["sys.* (4)"]]
    ns_dut[["dut.* (7)"]]
    ns_registers[["registers.* (7)"]]
    ns_rf[["rf.* (5)"]]
    ns_automation[["automation.* (1)"]]
    ns_activity[["activity.* (1)"]]
    ns_instruments[["instruments.* (13)"]]
    ns_memory[["memory.* (2)"]]
    ns_advanced[["advanced.* (7)"]]
    Registers -->|4| ns_registers
    Watch -->|3| ns_registers
    Actions_and_sequences -->|1| ns_automation
    Actions_and_sequences -->|1| ns_activity
    Dumps -->|1| ns_registers
    Radio -->|1| ns_dut
    Radio -->|1| ns_rf
    Instruments -->|11| ns_instruments
    Instruments -->|2| ns_rf
    Instruments -->|1| ns_activity
    Advanced -->|7| ns_advanced
    Advanced -->|2| ns_memory
    Connection_and_settings -->|6| ns_dut
    Connection_and_settings -->|1| ns_registers
    Connection_and_settings -->|2| ns_sys
    bgsvc["services on their own<br/>startup, live watch, connects"]
    bgsvc -.-> ns_sys
    bgsvc -.-> ns_registers
    bgsvc -.-> ns_rf
    bgsvc -.-> ns_instruments
    bgsvc -.-> ns_dut
```

### Registers

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    PeripheralTreeViewModel["PeripheralTreeViewModel"]
    RegisterDetailViewModel["RegisterDetailViewModel"]
    RegisterShortcutsViewModel["RegisterShortcutsViewModel"]
    HistoryViewModel["HistoryViewModel"]
    registers_read(["registers.read"])
    registers_read_many(["registers.read_many"])
    registers_write(["registers.write"])
    registers_write_field(["registers.write_field"])
    PeripheralTreeViewModel --> registers_read
    RegisterDetailViewModel --> registers_read
    RegisterDetailViewModel --> registers_write
    RegisterDetailViewModel --> registers_write_field
    RegisterShortcutsViewModel --> registers_read
    RegisterShortcutsViewModel --> registers_read_many
    HistoryViewModel --> registers_read
    HistoryViewModel --> registers_write
    HistoryViewModel --> registers_write_field
```

### Watch

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    WatchListViewModel["WatchListViewModel"]
    DataLoggerViewModel["DataLoggerViewModel"]
    registers_read_many(["registers.read_many"])
    registers_write(["registers.write"])
    registers_write_field(["registers.write_field"])
    WatchListViewModel --> registers_read_many
    WatchListViewModel --> registers_write
    WatchListViewModel --> registers_write_field
    DataLoggerViewModel --> registers_read_many
```

### Actions and sequences

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    ActionsViewModel["ActionsViewModel"]
    SequencesViewModel["SequencesViewModel"]
    activity_abort(["activity.abort"])
    automation_seq_run(["automation.seq.run"])
    ActionsViewModel --> automation_seq_run
    SequencesViewModel --> activity_abort
    SequencesViewModel --> automation_seq_run
```

### Dumps

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    DumpsViewModel["DumpsViewModel"]
    registers_read(["registers.read"])
    DumpsViewModel --> registers_read
```

### Radio

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    LpwPhyViewModel["LpwPhyViewModel"]
    WifiPhyViewModel["WifiPhyViewModel"]
    PrsViewModel["PrsViewModel"]
    dut_load_phy(["dut.load_phy"])
    rf_prs_route(["rf.prs_route"])
    LpwPhyViewModel --> dut_load_phy
    WifiPhyViewModel --> dut_load_phy
    PrsViewModel --> rf_prs_route
```

### Instruments

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    InstrumentViewModel["InstrumentViewModel"]
    SignalGeneratorViewModel["SignalGeneratorViewModel"]
    RfSwitchViewModel["RfSwitchViewModel"]
    ChamberViewModel["ChamberViewModel"]
    EcaViewModel["EcaViewModel"]
    activity_abort(["activity.abort"])
    instruments_chamber_read(["instruments.chamber.read"])
    instruments_chamber_set_temp(["instruments.chamber.set_temp"])
    instruments_chamber_wait_stable(["instruments.chamber.wait_stable"])
    instruments_connect(["instruments.connect"])
    instruments_eca_capture(["instruments.eca.capture"])
    instruments_eca_result(["instruments.eca.result"])
    instruments_siggen_get(["instruments.siggen.get"])
    instruments_siggen_rf(["instruments.siggen.rf"])
    instruments_siggen_set(["instruments.siggen.set"])
    instruments_siggen_trigger(["instruments.siggen.trigger"])
    instruments_siggen_waveforms(["instruments.siggen.waveforms"])
    rf_connect(["rf.connect"])
    rf_disconnect(["rf.disconnect"])
    InstrumentViewModel --> instruments_connect
    SignalGeneratorViewModel --> instruments_siggen_get
    SignalGeneratorViewModel --> instruments_siggen_rf
    SignalGeneratorViewModel --> instruments_siggen_set
    SignalGeneratorViewModel --> instruments_siggen_trigger
    SignalGeneratorViewModel --> instruments_siggen_waveforms
    RfSwitchViewModel --> rf_connect
    RfSwitchViewModel --> rf_disconnect
    ChamberViewModel --> activity_abort
    ChamberViewModel --> instruments_chamber_read
    ChamberViewModel --> instruments_chamber_set_temp
    ChamberViewModel --> instruments_chamber_wait_stable
    EcaViewModel --> activity_abort
    EcaViewModel --> instruments_eca_capture
    EcaViewModel --> instruments_eca_result
```

### Advanced

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    ConsoleViewModel["ConsoleViewModel"]
    CustomFunctionsViewModel["CustomFunctionsViewModel"]
    DutControlViewModel["DutControlViewModel"]
    MemoryViewModel["MemoryViewModel"]
    advanced_console_close(["advanced.console.close"])
    advanced_console_exec(["advanced.console.exec"])
    advanced_console_names(["advanced.console.names"])
    advanced_console_open(["advanced.console.open"])
    advanced_custom_function(["advanced.custom_function"])
    advanced_dut_control_describe(["advanced.dut_control.describe"])
    advanced_dut_control_invoke(["advanced.dut_control.invoke"])
    memory_read(["memory.read"])
    memory_write(["memory.write"])
    ConsoleViewModel --> advanced_console_close
    ConsoleViewModel --> advanced_console_exec
    ConsoleViewModel --> advanced_console_names
    ConsoleViewModel --> advanced_console_open
    CustomFunctionsViewModel --> advanced_console_open
    CustomFunctionsViewModel --> advanced_custom_function
    DutControlViewModel --> advanced_dut_control_describe
    DutControlViewModel --> advanced_dut_control_invoke
    MemoryViewModel --> memory_read
    MemoryViewModel --> memory_write
```

### Connection and settings

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    ConnectionViewModel["ConnectionViewModel"]
    DisconnectRecoveryViewModel["DisconnectRecoveryViewModel"]
    FaultRecoveryViewModel["FaultRecoveryViewModel"]
    SystemInfoViewModel["SystemInfoViewModel"]
    HardwareConfigViewModel["HardwareConfigViewModel"]
    dut_connect(["dut.connect"])
    dut_disconnect(["dut.disconnect"])
    dut_info(["dut.info"])
    dut_probe(["dut.probe"])
    dut_reconnect(["dut.reconnect"])
    dut_set_rpc_timeout(["dut.set_rpc_timeout"])
    registers_tree(["registers.tree"])
    sys_recover(["sys.recover"])
    sys_status(["sys.status"])
    ConnectionViewModel --> dut_connect
    ConnectionViewModel --> dut_disconnect
    ConnectionViewModel --> registers_tree
    ConnectionViewModel --> sys_status
    DisconnectRecoveryViewModel --> dut_connect
    DisconnectRecoveryViewModel --> dut_reconnect
    DisconnectRecoveryViewModel --> registers_tree
    DisconnectRecoveryViewModel --> sys_status
    FaultRecoveryViewModel --> sys_recover
    SystemInfoViewModel --> dut_info
    HardwareConfigViewModel --> dut_probe
    HardwareConfigViewModel --> dut_set_rpc_timeout
```

### Calls services make on their own

```mermaid
%%{init: {"flowchart": {"curve": "stepBefore"}}}%%
flowchart LR
    sys_hello(["sys.hello"])
    sys_subscribe(["sys.subscribe"])
    sys_status(["sys.status"])
    registers_watch(["registers.watch"])
    registers_unwatch(["registers.unwatch"])
    rf_paths(["rf.paths"])
    instruments_eca_sources(["instruments.eca.sources"])
    rf_prs_signals(["rf.prs_signals"])
    dut_info(["dut.info"])
    ConnectionService["ConnectionService"]
    EcaService["EcaService"]
    PrsService["PrsService"]
    RfSwitchService["RfSwitchService"]
    SystemInfoViewModel_via_ConnectionService["SystemInfoViewModel via ConnectionService"]
    WatchService__DataLoggerService["WatchService, DataLoggerService"]
    ConnectionService -->|startup| sys_hello
    ConnectionService -->|startup| sys_subscribe
    ConnectionService -->|startup, after connect| sys_status
    WatchService__DataLoggerService -->|Live / Record| registers_watch
    WatchService__DataLoggerService -->|Pause / Stop| registers_unwatch
    RfSwitchService -->|RF switch connects| rf_paths
    EcaService -->|ECA connects| instruments_eca_sources
    PrsService -->|DUT connects| rf_prs_signals
    SystemInfoViewModel_via_ConnectionService -->|DUT connects| dut_info
```

### Events

| Event (pushed after `sys.subscribe`) | Who listens | What it does |
|---|---|---|
| `status.changed` (`StatusChanged`) | ConnectionService | `StationState.apply_status`: facts per position, instruments |
| `dut.disconnected` (`DutDisconnected`) | ConnectionService | `StationState.mark_disconnected`; recovery dialog, sessions end |
| `watch.values` (`WatchValues`) | WatchService, DataLoggerService | new values for the watch list and the logger plot |
| `activity.progress`, `activity.finished` | ActivityTracker → ActionService, SequenceService, InstrumentBench | run and instrument progress |
| `log` (`LogLine`) | LogService | the Log panel |
| `call.late` (`CallLate`) | LogService | how a call that timed out finally ended |

### All endpoints

| Endpoint | Gateway method | Requires | Called by |
|---|---|---|---|
| `activity.abort` | `abort_activity` | — | ChamberViewModel, EcaViewModel, SequencesViewModel |
| `advanced.console.close` | `console_close` | — | ConsoleViewModel |
| `advanced.console.exec` | `console_exec` | dut | ConsoleViewModel |
| `advanced.console.names` | `console_names` | — | ConsoleViewModel |
| `advanced.console.open` | `console_open` | dut | ConsoleViewModel, CustomFunctionsViewModel |
| `advanced.custom_function` | `custom_function` | dut, idle | CustomFunctionsViewModel |
| `advanced.dut_control.describe` | `dut_control_describe` | dut | DutControlViewModel |
| `advanced.dut_control.invoke` | `dut_control_invoke` | dut, idle | DutControlViewModel |
| `automation.seq.run` | `run_sequence` | dut, idle, no_fault | ActionsViewModel, SequencesViewModel |
| `dut.connect` | `connect_dut` | no_fault | ConnectionViewModel, DisconnectRecoveryViewModel |
| `dut.disconnect` | `disconnect_dut` | — | ConnectionViewModel |
| `dut.info` | `dut_info` | dut | SystemInfoViewModel, SystemInfoViewModel via ConnectionService (DUT connects) |
| `dut.load_phy` | `load_phy` | dut, idle | LpwPhyViewModel, WifiPhyViewModel |
| `dut.probe` | `probe` | — | HardwareConfigViewModel |
| `dut.reconnect` | `reconnect_dut` | no_fault | DisconnectRecoveryViewModel |
| `dut.set_rpc_timeout` | `set_rpc_timeout` | — | HardwareConfigViewModel |
| `instruments.chamber.read` | `chamber_read` | instrument:chamber | ChamberViewModel |
| `instruments.chamber.set_temp` | `chamber_set_temp` | instrument:chamber, idle | ChamberViewModel |
| `instruments.chamber.wait_stable` | `chamber_wait_stable` | instrument:chamber, idle | ChamberViewModel |
| `instruments.connect` | `connect_instrument` | — | InstrumentViewModel |
| `instruments.eca.capture` | `eca_capture` | instrument:eca, idle | EcaViewModel |
| `instruments.eca.result` | `eca_result` | — | EcaViewModel |
| `instruments.eca.sources` | `eca_sources` | instrument:eca | EcaService (ECA connects) |
| `instruments.list` | `list_instruments` | — | not used by the frontend yet |
| `instruments.siggen.get` | `siggen_get` | instrument:signal_generator | SignalGeneratorViewModel |
| `instruments.siggen.rf` | `siggen_rf` | instrument:signal_generator | SignalGeneratorViewModel |
| `instruments.siggen.set` | `siggen_set` | instrument:signal_generator, idle | SignalGeneratorViewModel |
| `instruments.siggen.trigger` | `siggen_trigger` | instrument:signal_generator | SignalGeneratorViewModel |
| `instruments.siggen.waveforms` | `siggen_waveforms` | instrument:signal_generator | SignalGeneratorViewModel |
| `memory.read` | `memory_read` | dut | MemoryViewModel |
| `memory.write` | `memory_write` | dut, idle | MemoryViewModel |
| `registers.read` | `read_register` | dut | DumpsViewModel, HistoryViewModel, PeripheralTreeViewModel, RegisterDetailViewModel, RegisterShortcutsViewModel |
| `registers.read_many` | `read_many` | dut | DataLoggerViewModel, RegisterShortcutsViewModel, WatchListViewModel |
| `registers.tree` | `register_tree` | dut | ConnectionViewModel, DisconnectRecoveryViewModel |
| `registers.unwatch` | `unwatch` | — | WatchService, DataLoggerService (Pause / Stop) |
| `registers.watch` | `watch` | dut | WatchService, DataLoggerService (Live / Record) |
| `registers.write` | `write_register` | dut, idle | HistoryViewModel, RegisterDetailViewModel, WatchListViewModel |
| `registers.write_field` | `write_field` | dut, idle | HistoryViewModel, RegisterDetailViewModel, WatchListViewModel |
| `rf.connect` | `rf_connect` | instrument:rf_switch | RfSwitchViewModel |
| `rf.disconnect` | `rf_disconnect` | instrument:rf_switch | RfSwitchViewModel |
| `rf.paths` | `rf_paths` | instrument:rf_switch | RfSwitchService (RF switch connects) |
| `rf.prs_route` | `prs_route` | dut | PrsViewModel |
| `rf.prs_signals` | `prs_signals` | dut | PrsService (DUT connects) |
| `sys.hello` | `hello` | — | ConnectionService (startup) |
| `sys.recover` | `recover` | — | FaultRecoveryViewModel |
| `sys.status` | `status` | — | ConnectionViewModel, DisconnectRecoveryViewModel, ConnectionService (startup, after connect) |
| `sys.subscribe` | `subscribe` | — | ConnectionService (startup) |

"Requires" is the client's copy of the service's rule table (`core/requires.py`); the GUI disables a button
while a requirement is missing and the service refuses the call with `wrong_state`.
