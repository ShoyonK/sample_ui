# Product

<!-- impeccable:product-schema 1 -->

## Platform

desktop

Windows desktop application (PyQt5 + QML, Python 3.10.5), shipped as a PyInstaller exe on station PCs.
Not a web app: none of the web/iOS/Android platform values apply.

## Users

- **RF/radio validation engineers** bring up and characterize radio behavior on DUTs at a test station.
  They load PHYs, route PRS signals, drive instruments (signal generator, RF switch, chamber, ECA), and
  compare chip state against Radio Calculator configs.
- **Firmware and silicon debug engineers** read and write registers, fields and memory while debugging a
  chip, often alongside a test paused in a debugger.

Both are expert users who know the chip's register map and work at the bench for long sessions.

## Product Purpose

SiRAT (Silicon Labs Register Access Tool) gives engineers direct, safe access to a connected DUT at one of a
station's four positions. They can browse and edit registers, watch and log values over time, take and
compare dumps, load PHYs, control instruments, and capture repeatable work as actions, sequences, sessions
and generated Python test code.

The new SiRAT replaces the original floating-dialog GUI. It succeeds when engineers:
- get **safer hardware access**: the Station API service enforces requires rules, critical-write
  confirmation and read-back verification, so a stale or buggy GUI can't put a DUT in a bad state;
- have a **faster daily workflow**: one window with pages instead of about 15 floating dialogs, and quicker
  read, write and watch loops;
- can **reproduce their work**: actions, sequences, sessions and generated code make bench work repeatable;
- can switch **as a drop-in replacement**: the same settings files and workflows, so they switch without
  retraining.

## Positioning

A thin client of the typed Station API. Hardware access, safety rules and state (facts + requires) live in
the station service, and the GUI mirrors them to enable or disable actions. The GUI never imports the bench,
switch or DUT-control libraries directly.

## Operating Context

- Lab test stations running Windows, with up to four DUT positions plus bench instruments.
- Long hands-on sessions mixing exploration (browse, read, poke) with repeatable setup (actions, sequences).
- Used next to the test codebase. Generated code is pasted into tests, and debug mode attaches to a test
  paused in PyCharm.
- Until the Station API exists, development and demos run against an in-memory fake backend with named
  scenarios (`happy`, `flaky_dut`, `slow_rpc`, `disconnected_at_start`, `everest`).

## Capabilities and Constraints

- **Requirements.** Feature scope comes from `sirat_requirements.txt` (35 features). It's read for the
  function each feature provides, not copied literally where the original behavior doesn't make sense.
- **API contract.** `docs/API_DESIGN.md` (revision 2, draft) supersedes the Oct 27
  `SiRAT Station API Design Document.pdf`. Four of its decisions are still open.
- **Architecture.**
  - Strict MVVM, with services organized by domain.
  - Every visual unit is split into `XxxForm.ui.qml` (layout only, editable in Qt Design Studio) and
    `Xxx.qml` (wiring).
  - Strong typing at boundaries (pyrefly), and pydantic validation of everything read from disk.
- **Compatibility.** Settings files keep the original SiRAT formats and locations (`~/.sirat_*.json`,
  `~/.sirat/*.json`), so the old and new GUIs can share a home folder.
- **Testing.** Behavior-focused unit, integration and e2e tests against the fake backend. Any QML warning
  fails an e2e test.
- **Windows.** Main pages, the watch list, the data logger and individual graphs can pop out into their own
  windows.
- **Terminology.** DUT, position (1–4), PHY (LPW / WiFi), PRS, peripheral / register / field, critical
  peripheral, read-sensitive peripheral, action, sequence, dump, Radio Calculator diff, siggen, ECA.
- **Undecided** (see docs/API_DESIGN.md §11):
  - whether actions stay GUI-owned;
  - whether `radio.*` stays out of v1;
  - the opt-in rule for read-sensitive registers;
  - where the test list comes from.

## Brand Commitments

- The product name is SiRAT, a Silicon Labs internal tool.
- The visual direction was set from the "Sequence Editor" mockup (`docs/mockups/sirat_mockup.html`), and the
  current app implements it in the QML `Theme` singleton. This is an existing direction, not a recorded
  DESIGN.md.

## Evidence on Hand

- Requirements: `sirat_requirements.txt`.
- API: `SiRAT Station API Design Document.pdf`, `docs/API_DESIGN.md`, `docs/API_REVIEW.md`, and
  `docs/API_CHANGE_*.md`.
- Plans and status: `docs/FRONTEND_PLAN.md` and `docs/GAP_REVIEW.md`.
- Look and samples: the screenshots in `docs/screenshots`, the mockup in `docs/mockups/sirat_mockup.html`,
  and the sample Radio Calculator config in `docs/samples/PHY_demo.cfg`.
- **No real hardware data or user research.** Everything runs against the fake backend. Don't fabricate
  user quotes, adoption numbers or performance claims.

## Product Principles

1. **Safety is enforced, not hoped for.** Any action that can damage a DUT is gated by the service's rules.
   The GUI explains why something is disabled rather than hiding it.
2. **Expert speed over hand-holding.** Dense, scannable views, short paths from seeing a value to changing
   it, and no confirmations beyond the ones safety needs.
3. **Everything repeatable.** Anything done by hand should be easy to save as an action, a sequence, a
   session or code.
4. **Familiar to existing users.** Keep the original workflows, file formats and terminology unless the
   change is clearly better and explained.
5. **Honest about state.** Connection, PHY, activity and fault state are always visible and never guessed.
