# SiRAT frontend

PyQt5 + QML frontend for SiRAT, built with strict MVVM. Until the Station API service exists, it runs
against an in-memory fake that follows the same contract (requires rules, error codes, events).

- Plan and class diagrams: [docs/FRONTEND_PLAN.md](docs/FRONTEND_PLAN.md)
- Screenshots of the real app: [docs/screenshots](docs/screenshots)

## Run

Needs [uv](https://docs.astral.sh/uv/). It installs Python 3.10.5 and the dependencies itself.

```bash
uv sync
uv run sirat
```

Options:

| Flag | Meaning |
|---|---|
| `--scenario happy` | connected DUT, normal latency (default) |
| `--scenario flaky_dut` | the DUT drops after a few reads (try the recovery dialog) |
| `--scenario slow_rpc` | every call is about 10x slower (see busy states) |
| `--scenario disconnected_at_start` | start disconnected and use the Connect sheet |
| `--home PATH` | where settings live. The fake backend defaults to `~/.sirat/demo_home` so it never touches real SiRAT settings |
| `--no-demo-data` | don't seed demo favorites, actions and sequences |

Session logs go to `C:/temp/sirat/session_log_<timestamp>.log`.

Settings files use the original SiRAT formats (`~/.sirat_favorites.json`, `~/.sirat_watch_list.json`,
`~/.sirat_data_logger.json`, `~/.sirat_sequences.json` …), so the old and new GUIs can share a home folder.
See `src/sirat_ui/stores/formats.py`.

From Python (for example a PyCharm debug console): `from sirat_ui.app.launch import launch_viewer; launch_viewer()`.

## Test

```bash
uv run pytest
```

| Folder | What it checks |
|---|---|
| `tests/unit/core` | bit math (property tests), parsing, search rules, formulas, requires table, actions, codegen |
| `tests/unit/gateway` | the fake behaves like the API contract |
| `tests/unit/domains` | user behaviour through ViewModels: read, write, confirm, verify, favorites, watch, sequences … |
| `tests/integration` | cross-tab behaviour with the real container: connect, disconnect recovery, persistence across restarts |
| `tests/e2e` | real QML window driven by mouse and keyboard through page objects; any QML warning fails the test |
| `tests/unit/test_architecture.py` | layering rules, file size, and the `.ui.qml` rules for Design Studio |

Tests use a `ManualScheduler` and never sleep. Tests reference `@pytest.mark.req("5.write")` IDs, which point at
sections of `sirat_requirements.txt`.

## Build the executable

```bash
uv run python build_exe.py
```

This produces `dist/SiRAT.exe`, a single file that needs no Python or Qt installed. The bundle carries only the Qt
the app uses, so a new QML import has to be added to `KEEP` in `packaging/sirat.spec`.

## Layout

```
src/sirat_ui/
  app/          bootstrap: Application, ServiceContainer (composition root), launch, Qt scheduler
  core/         pure Python: registers, bits, formatting, search, requires, formulas, actions, codegen
  gateway/      StationGateway port, Call, errors, events + fake/ (in-memory station, scenarios)
  state/        AppState (global cross-tab state), Preferences
  stores/       JSON persistence (same file names as today's SiRAT) + demo data
  shared/       ViewModel base + list model, InteractionService, DialogsViewModel, ErrorPresenter
  domains/      one folder per feature: service + ViewModels
    connection/ registers/ annotations/ monitoring/ automation/ history/ logs/ shell/
  qml/
    theme/      Theme singleton (all colors, spacing, fonts; dark mode)
    components/ design system: AppButton, Card, Chip, SegmentedControl, Sparkline …
    shell/      window chrome: top bar, nav rail, page host, bottom dock, status bar
    pages/      registers/ watch/ actions/ sequences/ settings/ dock/ placeholder/
    dialogs/    confirm, alert, prompt, disconnect recovery, connect sheet, toasts
```

### Design Studio

Open `designstudio/SiRAT.qmlproject`. Each screen is split into two files:

- `XxxForm.ui.qml`: layout only. Edit these in Design Studio.
- `Xxx.qml`: binds the form to its ViewModel. Edit these in code.

The forms contain no logic and no ViewModel references; `tests/unit/test_architecture.py` enforces this.

## Type checking

The package type-checks with [pyrefly](https://pyrefly.org) (config in `pyproject.toml`):

```bash
uv run pyrefly check
```

`tests/unit/test_typing.py` runs it with the test suite, so a type error fails the tests. Qt names that PyQt5's
stubs miss or mistype come from `sirat_ui.shared.qt`.

## Validating what comes from disk

Settings files, sessions and settings exports are validated with pydantic when they're loaded
(`src/sirat_ui/stores/schemas/`). Invalid entries are skipped, not fatal: each one is written to the Log panel,
a toast says how many were skipped, and the original file is copied to `<file>.bak` before anything can
overwrite it. An action with any invalid operation is skipped as a whole, so half an action never runs.
Inside the app, plain dataclasses are used and pyrefly checks them.
