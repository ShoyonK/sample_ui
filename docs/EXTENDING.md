# Extending the SiBench frontend

How to add the common kinds of feature, and every file each one touches. Paths are under `src/sibench_ui/`
unless they start with `tests/`, `docs/` or `scripts/`. See [ARCHITECTURE.md](ARCHITECTURE.md) for how the
pieces fit together.

```mermaid
%%{init: {"flowchart": {"curve": "stepAfter"}}}%%
flowchart TD
    start{"What are you adding?"}
    start -->|"a screen in the nav rail"| page["1. A page"]
    start -->|"a card, panel or dialog on a page"| vm["2. A ViewModel and its QML"]
    start -->|"a new kind of step in an action"| op["3. An operation kind"]
    start -->|"Add to Actions on a page"| rec["4. Add to Actions"]
    start -->|"logic that calls the station"| svc["5. A service"]
    start -->|"a call the station must answer"| ep["6. A station endpoint"]
    start -->|"something saved in ~/.sibench"| store["7. A settings file"]
    start -->|"an entry in Ctrl+K"| cmd["8. A Ctrl+K command"]
    start -->|"a confirm, prompt or custom dialog"| dlg["9. A dialog"]
    page --> vm
    vm --> svc
    svc --> ep
    rec --> op
```

The rules the tests enforce (`tests/unit/test_architecture.py`) apply to everything below:

- Services take the gateway area they need (`RegistersPort`, `InstrumentsPort`, …), never `StationGateway`.
- ViewModels never import `gateway.port` or `ErrorPresenter`; they call services.
- Services report station failures with `ErrorPresenter.present(error, context)`; ViewModels show results
  inline and toast only input and file problems.
- Qt properties: `qprop(type, "_attr", changed)` for stored values, `@pyqtProperty(type, notify=changed)`
  for computed ones. No lambda properties.
- `.ui.qml` forms contain layout only: no handlers, functions, `app.` or `vm.`; every interactive control has
  an `objectName`; every form has a wrapper `.qml` next to it; font sizes come from `Theme`.
- Aim for Python files of about 600 lines; 900 is the hard limit. `models/` imports only the standard library and other models.

Button colors (`AppButton` `variant`) follow one rule, so color tells the user what a button does:

| Variant | Looks | Use for |
|---|---|---|
| `run` | solid red | Starts something on the DUT or an instrument that keeps going until it ends or is stopped: Run, Run checked, Execute, Start capture, Start recording, Infinite trigger, Wait for stable |
| `primary` | solid black | The one main action of a card or dialog: Apply, Save, Connect, Load PHY, Write, OK, Take a dump. At most one per card. Reads can be black this way, but never red: they don't change the DUT |
| `danger` | red text | Destructive or stopping: Delete, Remove, Clear all, Clear data (the logger's samples), Stop, Disconnect |
| `secondary` | white (default) | Everything else, including one-shot actions like Single trigger |
| `ghost` | text only | Minor helpers that lose nothing: Collapse all, Reset zoom, Clear (a result view) |

A button that turns into its own Stop while running switches `run` to `danger` (Sequences, the logger).

---

## 1. A page

A page is one row in the page table plus the ViewModels its QML binds. The nav rail, page host, pop-out
windows and the "every page loads" test all read the table.

| File | Change | |
|---|---|---|
| `domains/shell/pages.py` | Add a row: `key`, `title`, `label` (nav rail), `icon`, `ready`, `source` (QML path relative to `qml/shell/`) | required |
| `qml/pages/<key>/<Name>Page.qml` | Wrapper: binds the form to `app.<vm>` and calls slots | required |
| `qml/pages/<key>/<Name>PageForm.ui.qml` | Form: layout only, `property alias` for every control the wrapper touches | required |
| ViewModels for the page | See [2. A ViewModel](#2-a-viewmodel-and-its-qml) | required |
| `domains/shell/tools.py` | A `Tool` row for each part that should open in its own window (title, QML file, window size; `fill=True` if it fills the window rather than keeping a card's height). Put `ToolSlot { toolKey: "<key>" }` in the form where the part goes: it shows the part, or a placeholder while it's popped out. The nav rail's right-click menu lists the parts | optional |
| `qml/components/Icon.qml` | Only if no existing glyph fits (`glyphs` map) | optional |
| `app/commands.py` | A Ctrl+K entry that opens the page ([8](#8-a-ctrlk-command)) | optional |
| `tests/e2e/test_journeys.py` | A journey through the page; the load test picks the page up from `pages.py` already | recommended |
| `scripts/screenshot.py`, `docs/GAP_REVIEW.md` | A screenshot and the requirement rows marked done | recommended |

The page keeps its state after the first visit (`PageLoader` loads lazily and doesn't unload), so start polling
in `onVisibleChanged` only if it should stop when hidden (see `ChamberCard.qml`).

## 2. A ViewModel and its QML

| File | Change | |
|---|---|---|
| `domains/<area>/<thing>_viewmodel.py` | `class XViewModel(BaseViewModel)` with `changed = pyqtSignal()`, properties (`qprop` / `@pyqtProperty`), slots (`@pyqtSlot`). Take services and state stores in the constructor | required |
| `app/container.py` | Construct it in the area's `_<area>_viewmodels()` method and return it under the name QML uses: `"myThing": MyThingViewModel(...)` makes `app.myThing` | required |
| `qml/pages/<area>/<Thing>.qml` + `<Thing>Form.ui.qml` | Wrapper binds `vm.prop` and calls `vm.slot()`; form holds the layout | required |
| `tests/unit/domains/test_<area>.py` | Behaviour tests through `harness.shell.myThing` against the fake (`harness` fixture in `tests/conftest.py`) | required |

Which state store to inject:

| Need | Inject |
|---|---|
| connected?, DUT position, chip, `can(method)` for enabling buttons | `StationState` |
| the open register or peripheral | `SelectionState` |
| value format, dark mode, other preferences | `PreferencesState` |
| set the status bar message | `StatusLine` (services usually do this, not ViewModels) |

A new area builder method also needs adding to the tuple in `ServiceContainer._build_viewmodels`.

## 3. An operation kind

Operations are the steps saved in an action (`~/.sibench/actions.json`) and sent with `automation.seq.run`.
Each kind is defined once in `core/ops.py`; `tests/unit/core/test_ops.py` fails until the schema and the
color exist.

| File | Change | |
|---|---|---|
| `core/ops.py` | `_register(OpKind("my_kind", describe=…, code=…, wire_fields=(…) or to_wire=…, carries_code=…, editable=…))` | required |
| `stores/schemas/operations.py` | A pydantic model with `type: Literal["my_kind"]`, added to `OPERATION_MODELS` (the file schema) | required |
| `qml/theme/Theme.qml` | A color in both maps of `kindColor` (light and dark), or a tone in `kindTone` | required |
| `gateway/fake/fake_station.py` | Handle the kind in `_execute_op` so sequences can run it against the fake | required |
| `station_protocol/automation.py` | The op's wire shape (a `TypedDict` with `type: Literal["my_kind"]`), added to `WireOp`, so the station validates it | required |
| `docs/STATION_API.md` | The op in section 11, so the real service implements it; then `uv run python scripts/api/build.py` | required |
| `tests/unit/domains/…` | A test that records and runs the kind | recommended |

`describe` is what the Actions list shows, `code` returns the lines for Generate code (req 16), and the wire
shape is `{"type": kind, **wire_fields}` unless `to_wire` builds it (see `signal_generator`, `custom_function`).

## 4. Add to Actions on a page

| File | Change | |
|---|---|---|
| the page's service | Take `actions: ActionRecorder` (`domains/automation/recorder.py`) and add `add_action(...) -> Action` that calls `self._actions.add(name, [op])`; `add()` makes the name unique | required |
| the page's ViewModel | An `addToActions()` slot that calls the service and toasts `Added <name> to Actions` | required |
| `app/container.py` | Pass `actions` (the `ActionService`) to the service | required |
| the page's form and wrapper | An `Add to Actions` button (`objectName`, `iconName: "bolt"`) bound to the slot | required |
| `core/ops.py` and the rest of [3](#3-an-operation-kind) | Only if the op is a new kind | conditional |

## 5. A service

| File | Change | |
|---|---|---|
| `domains/<area>/<name>.py` | The class. Constructor takes the narrowest gateway area (`gateway/port.py`), the state stores, `ErrorPresenter`, `LogService`, other services. Expose an `Event` (`core/observable.py`) for ViewModels to follow | required |
| `app/container.py` | Add a field to the `Services` dataclass and construct it in `_build_services()` | required |
| `app/container.py` `reload_user_data()` | Add it to the list if it reads a settings file | conditional |
| `app/container.py` `stop()` | Stop its timers if it polls (see `ChamberService.stop_polling`) | conditional |
| `tests/unit/domains/test_<area>.py` | Behaviour tests through its ViewModel | required |

Long-running station work (an activity) goes through `ActivityTracker.follow(activity_id, on_progress,
on_done)`; don't subscribe to `gateway.events` yourself for activities.

## 6. A station endpoint

An endpoint is an API method the real station service must answer (`docs/STATION_API.md`).

| File | Change | |
|---|---|---|
| `docs/STATION_API.md` | What the method does, its errors and the facts and events it changes (section 8) | required |
| `station_protocol/<group>.py` | Its `Method` in the group's `METHODS`: wire name, parameters with their wire types and ranges (in the order the gateway method takes them), result type, `wrap` and `requires`; a new result type is a dataclass there. A new group is a new module, added to `catalog.GROUPS` | required |
| `gateway/port.py` | The method on its area interface (or a new area interface added to `StationGateway`), returning `Call[Result]` | required |
| `gateway/wire/bindings.py` | `"attr": "area.method"` in `WIRE_OF` (the parameters and types come from the two sides; loading checks they agree) | required |
| `gateway/api/client.py` | The method on `ApiStationGateway`: `return self._call("attr", ...)` | required |
| `models/station.py` | The app's result dataclass, if new: the same name and fields as the protocol's (a test compares them) | conditional |
| `core/requires.py` | Only a new tag: its wording in `TAG_TEXT` (the tags themselves are the protocol method's `requires`) | conditional |
| `gateway/fake/fake_station.py` | `def method(...)`: `return self._respond("area.method", position, run, **params)`. Instrument calls use `_instrument_call`; memory and Python calls live in `gateway/fake/advanced.py` (`FakeAdvanced` plus a one-line method on `AdvancedMethods`) | required |
| the service that uses it | Call it, report failures with `ErrorPresenter` | required |
| `tests/unit/gateway/test_fake_station.py` | The fake answers it and refuses it when requires aren't met | recommended |
| `scripts/api/build.py` | A sample call in `Capture.run`; then `uv run python scripts/api/build.py` regenerates `docs/STATION_API_REFERENCE.md` and `docs/station_api.schema.json` (a test fails until you do) | required |
| `tests/contract/` | A call over TCP by its wire name (`station.call("area.method", ...)`); the result is checked against the protocol type | recommended |

The fake must keep the same rules as the real service (requires, error codes), or the GUI will rely on
behaviour the real backend won't have.

## 7. A settings file

Files in `~/.sibench/` (or `~/.sibench_*.json` for formats shared with the old GUI) are loaded through pydantic
cleaners, so a bad entry is skipped and reported instead of crashing.

| File | Change | |
|---|---|---|
| `stores/schemas/files.py` | A pydantic model and a `clean_<name>(raw, report)` function | required |
| `stores/schemas/__init__.py` | Import it and add it to `CLEANERS` | required |
| `stores/json_store.py` | A `UserStores` field, its `JsonStore(path, default, CLEANERS[...])` in `in_home()`, and add it to `all()` | required |
| `domains/settings/transfer.py` | Add it to `_named()` so export, import and Clear all include it | required |
| the service that owns it | Read with `store.load()`, write with `store.save(data)`, and a `reload()` | required |
| `app/container.py` | Pass the store to the service; add the service to `reload_user_data()` | required |
| `tests/unit/domains/test_settings.py` | Bump the `"Imported N settings files"` count | required |
| `docs/FRONTEND_PLAN.md` | The file in the persistence list | recommended |

## 8. A Ctrl+K command

| File | Change | |
|---|---|---|
| `app/commands.py` | `Command(key, title, subtitle, run, shortcut="")` in `palette_commands()`. `go("page", then)` opens a page first. A `shortcut` (Qt key sequence) is bound by `Main.qml` and shown in the palette automatically | required |
| `app/commands.py` + `app/container.py` `_palette()` | If the command calls a ViewModel the function doesn't receive yet, add a parameter and pass `cast(XViewModel, vms["x"])` | conditional |

## 9. A dialog

Standard dialogs need no QML: a service or ViewModel calls `InteractionService`
(`shared/interactions.py`): `confirm(ConfirmRequest)`, `prompt(PromptRequest)`, `alert(Alert)`,
`toast(level, text)`, `choose_open_file(...)`, `choose_save_file(...)`, `show_code(title, code)`. The request
types are in `models/dialogs.py`; tests answer them with `harness.ix.answer_next(...)`.

A custom dialog:

| File | Change | |
|---|---|---|
| `qml/dialogs/<Name>Dialog.qml` | Built on `ModalDialog`, `shown: vm.isOpen` (not `visible`: a dialog reopened during its closing animation would stay closed) | required |
| `qml/shell/DialogHost.qml` | Add `<Name>Dialog { }` | required |
| a ViewModel | `isOpen` property and open/close slots; register it in the container | required |

---

## Before you're done

```bash
uv run pytest -q
```

```bash
uv run pyrefly check
```

```bash
uv run python scripts/screenshot.py
```

Then update `docs/GAP_REVIEW.md` for the requirement. If classes, signatures or station calls changed,
regenerate the diagrams:

```bash
uv run python scripts/architecture/build.py
```
