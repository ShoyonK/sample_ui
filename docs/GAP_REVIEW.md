# Requirements gap review

**Date:** 2026-10-27
**Compared:** `sirat_requirements.txt` (USER, FUNCTIONAL and UI requirements of all 35 sections) against the current frontend in `src/sirat_ui`.

Legend:

| Mark | Meaning |
|---|---|
| ✅ | Done and tested |
| 🟡 | Built, but parts of the requirement are missing or different |
| ❌ | In a built area, but not implemented |
| 🗓 | Whole page planned for a later phase (placeholder in the app today) |

Priority:

| Priority | Meaning |
|---|---|
| **P1** | Bugs: data-compatibility problems or behaviour that contradicts a requirement |
| **P2** | Missing pieces of features that are already on screen |
| **P3** | Missing features that need a new page or dialog |
| **Later** | Planned phases (6 and 7 in the frontend plan) |

## Summary

| Area | Sections | Status |
|---|---|---|
| Launch, layout, menus | §1, §2 | ✅ Done (File/Help items live on the Settings page) |
| Connection, recovery | §3 | 🟡 PHY buttons wait on the Radio page |
| Tree, search, detail, access policy | §4–§7 | ✅ Done |
| Favorites, notes | §8, §10 | ✅ Done |
| History | §9 | ✅ Done |
| Formulas | §11 | ✅ Done |
| Actions | §13 | ✅ Done |
| Sequences | §14 | ✅ Done |
| Code generation | §16 | ✅ Done |
| Data logger | §17 | ✅ Fixed in the last round |
| Watch list | §18 | ✅ Done |
| System info, hardware config | §31, §32 | ✅ Done |
| Sessions | §34 | ✅ Done |
| Dumps | §12 | ✅ Done |
| Radio Calculator diff | §21 | ✅ Done |
| PHY loaders, PRS routing | §23, §24 | ✅ Done (Radio and PHY page) |
| Logging | §35 | ✅ Done |
| Dumps, Radio Calculator diff, custom functions, memory viewer, console, API explorer, PHY, PRS, instruments, ECA, tests | §12, §15, §19–§30, §33 | 🗓 Planned pages |

---

## P1: bugs and compatibility problems ✅ fixed 2026-10-27

All eight are fixed and covered by tests tagged `11.persist`, `11.format`, `14.skip-disabled`, `14.missing-action`, `9.field-write`, `18.format` and `35.persist`. Log files: both the §1 session log and the §35 daily log are written.

| # | § | Problem | Requirement | Today |
|---|---|---|---|---|
| 1 | 11 | **Formula file format is wrong.** Existing users' formulas won't load, and the old GUI can't read ours. | `{"SYNTH.FREQ": {"formula": "...", "unit": "Hz"}}` | `{"SYNTH.FREQ.FREQ": ["...", "Hz"]}` |
| 2 | 14 | **Sequences run disabled actions** and fail on a missing action instead of skipping it. | "If disabled: Skips"; "If not found: Logs warning, continues" | Every action in the sequence runs; a missing name is silently dropped without a warning |
| 3 | 14 | Sequence steps are shown **per operation, not per action**. | List and highlight the actions in the sequence (yellow while running) | One row per operation, so the user can't see or edit the actions themselves |
| 4 | 11 | Calculated values are formatted differently. | 3 decimals if \|x\| ≥ 1, else 6 decimals ("2440.125 MHz") | Whole numbers drop decimals ("-76 dBm") |
| 5 | 11 | `pow` isn't allowed in formulas. | Allowed functions: abs, round, min, max, **pow** | pow missing; extra functions (sqrt, log …) allowed |
| 6 | 9 | Field writes look the same as register writes in History. | Yellow row; "WRITE REG.FIELD ← 0x1 (full register: 0x…)" | Green WRITE chip; no full register value shown |
| 7 | 18 | Watch list values ignore the display format. | Hex/Dec/Bin follows the main window setting | Always hex |
| 8 | 1, 35 | **Log file locations conflict.** | §1: `C:/temp/sirat/session_log_<ts>.log`. §35: `~/.sirat/logs/sirat_{date}.log`, daily, keep 30 days, `[YYYY-MM-DD HH:MM:SS.mmm] [LEVEL]` | Only the §1 session log. **Needs your call:** write both, or pick one |

## P2: missing pieces of features already on screen

### Actions (§13) ✅ done 2026-10-27
- ✅ View dialog (operations read-only; embedded code syntax highlighted)
- ✅ Edit dialog (register/field values editable with range checks; other kinds shown as info)
- ✅ Deselect all
- ✅ Per-type color bar, icon and chip (§13 colors, light and dark variants)
- ✅ Add checked actions to a new or existing sequence
- ✅ Run output console under the large Actions view
- ✅ Add reconnect to Actions from the disconnect dialog (§3)

### Sequences (§14) ✅ done 2026-10-27
- ✅ Add action… picker, Remove, Up/Down for the selected action
- ✅ Rename (keeps position and description; refuses duplicate names)
- ✅ Add to Actions panel (a `sequence` operation)
- ✅ Console with colored output, Clear, and completion summary
- ✅ New sequences start empty, as §14 describes
- 🟡 List text is two lines ("3 actions · description") instead of "Name (5 actions)"; same information

### History (§9) ✅ done 2026-10-27
- ✅ Click / Ctrl+click / Shift+click selection
- ✅ Right-click "Save selected…" to JSON in the §9 format (native save dialog)
- ✅ Generate code from history (selected entries, or all)

### Formulas (§11) ✅ done 2026-10-27
- ✅ Formula dialog: help text, four clickable examples, Test (x = 100), Save, Remove with confirmation, Cancel
- ✅ Calculated column tooltip; note cell and not-read value tooltips (§5, §10)

### Code generation (§16) ✅ done 2026-10-27
- ✅ §16 script template (header with timestamp, imports, `main(dut)`, `__main__` block) and per-type snippets; custom function code inlined from `~/.sirat_custom_functions.json`
- ✅ Code dialog with Python highlighting, Copy to clipboard, Save to file…

### Watch list (§18) ✅ done 2026-10-27
- ✅ Write a value (double-click or right-click → Write value…; read-only fields refused)
- ✅ Ctrl/Shift multi-select, Delete selected, Add selected to logger, right-click Add to logger
- ✅ Rate field applies on Enter or leaving the field; out-of-range values rejected

### Logging (§35) ✅ done 2026-10-27
- ✅ One checkbox per level (Debug, Info, Warning, Error); Debug lines for register reads and writes
- ✅ Case-insensitive search with highlighted matches, "n of m", next/previous
- ✅ Save log… (native save dialog)
- ✅ Display format `[14:23:45.123] [INFO] …`
- ✅ Pop-out log window, synced with the dock panel

### Tree, detail, connection (§3–§5)
- ✅ **Read all registers progress dialog**: modal, cancelable, "Reading {periph}.{reg}…", X of Y; reads one register at a time, skips write-only and read-sensitive registers, stops if the DUT drops, summary at the end.
- ✅ **Add reconnect to Actions** from the disconnect dialog (§3 user requirement).
- 🟡 **"Load LPW PHY" / "Load WiFi PHY"** in the recovery dialog should open the PHY loaders (§23). Today they load fixed PHY names. This depends on the planned Radio page.
- ✅ **Not-read field tooltip**: "Value not read yet - may not be accurate".

### Favorites and notes (§8, §10)
- ✅ Favorites are **sorted alphabetically** (display only; the saved order is untouched).
- ✅ The note cell has the tooltip "Click to edit note".

### From our own plan (docs/FRONTEND_PLAN.md)
- ✅ **Ctrl+K command palette**: registers (also by field name), pages, actions, sequences and common commands; also opens from the top bar.
- ❌ **Component Gallery** page (living style guide).
- ❌ **Design Studio mock data** (`designstudio/mockups/`), so nested panels preview with sample data.
- ❌ **Requirements coverage report** from the `@pytest.mark.req` markers.

## P3: missing features that need a new page or dialog

| § | Feature | Notes |
|---|---|---|
| 2 | ✅ **File menu actions**: Export user settings…, Import user settings…, Clear all user settings… | On the Settings page; one JSON bundle; import and clear ask first and apply without a restart. |
| 2 | ✅ **Help**: Hardware configuration, About SiRAT | About shows SiRAT, station release, protocol, backend, Python and Qt versions. |
| 31 | ✅ **System information**: four §31 categories, Refresh, Copy all (§31 text format), auto-refresh on connect | API: `dut.info`. |
| 32 | ✅ **Hardware configuration**: host, port, timeout, position with §32 validation; `~/.sirat/hardware_config.json`; Save applies the timeout and position; Test connection leaves no connection behind | Host and port are an explicit per-connection override sent with `dut.connect` ("Use a specific RPC address", off by default), also on the Connect sheet. Needs the API change in `docs/API_CHANGE_dut_connect_rpc_address.md`. |
| 34 | ✅ **Sessions**: Save session… (name, summary), Load session… (list, preview, delete), auto-save every 5 min to `~/.sirat/autosave.json` | Contents: dumps, notes, formulas, actions, favorites, history. Files go in `~/.sirat/sessions/`. On the Settings page and in Ctrl+K. Dumps stay an empty list until the Dumps page exists. The auto-save also runs on exit and its history is restored on the next launch. |

## Later: planned pages (placeholders in the app today)

These were scoped to Phases 6 and 7 from the start, so they aren't oversights. They're listed so nothing is forgotten. Several feed **Add to Actions**, so the Actions feature is only complete once they exist.

| § | Page | Key requirements |
|---|---|---|
| 12 | ✅ Dumps | Take dump (select peripherals), compare two dumps, diff live vs dump, CSV files in `C:/temp/sirat/dumps/`. Done: Dumps page with saved dumps, Take a dump (picker, progress, name), Diff vs live, Compare with (a saved dump) and Compare files (two file dialogs), field-level Change column, Save report, Delete; dumps taken are kept in sessions. Radio Calculator diff (§21) is done too (see §21). |
| 21 | ✅ Radio Calculator diff | Load `PHY_<name>.cfg`, compare field by field, match/mismatch/error, summary, sortable table. Done on the Dumps page and in Ctrl+K: pick a .cfg, pick peripherals (field counts, all checked), progress, colour-coded results sortable by any column (Status sorts problems first), Save report. Each register is read once however many fields it has. Not done: auto-searching the workspace for `PHY_<name>.cfg` (the frontend has no workspace path yet). Sample: `docs/samples/PHY_demo.cfg`. |
| 15 | Custom functions | Editor with highlighting, run with output, shared namespace, add to Actions, `~/.sirat_custom_functions.json` |
| 19 | Memory viewer | Read 1–4096 bytes, write byte/word/dword, hex dump with ASCII, last address persisted |
| 20 | Python console | `advanced.py_exec`, history with arrow keys, help |
| 22 | DUT control API explorer | Browse the tree, signatures and docstrings, invoke with parameters, error hints, add to Actions |
| 23 | ✅ PHY loaders | LPW and WiFi parameters, packet structure preview, add to Actions. Done on the Radio and PHY page: LPW PHY by name, known list or file, success prompt offering Add to Actions; WiFi form with every §23 option (band-aware channels, standard-aware power modes and rates, TX and 11ax/be advanced sections), live packet diagram with airtime, success dialog with config, function and TestInputs overrides; WiFi only on Everest chips (`--scenario everest` to try it). Needs `docs/API_CHANGE_phy_and_prs.md`. Assumptions: MP power only for ax/be; 2.4 GHz bandwidth up to 40 MHz. |
| 24 | ✅ PRS routing | Signal/pin/channel, port and channel validation, active routes, add to Actions. Done: family signals via `rf.prs_signals` (fallback list if unavailable), categories, live A/B vs C/D hint plus the §24 warning on Apply, routes table with Remove (records the six register writes in History), routes cleared on disconnect. |
| 25–27 | Signal generator, BLE packet, GFSK | Role status, apply/trigger, overrides, packet builder, add to Actions |
| 28 | RF switch | Path and position, switch roles, add to Actions |
| 29 | Temperature chamber | Set, monitor, wait for stable |
| 30 | ECA capture | Configure, trigger, view, save (currently disabled in the original) |
| 33 | Test execution | Run, progress, pass/fail, output, stop |

---

## Suggested order

1. ~~**P1 batch**~~ done (one sitting): formula file format, sequence semantics (skip disabled, warn on missing, per-action steps), formula formatting and `pow`, History field-write display, watch format. Item 8 (log files) waits for your decision.
2. ~~**Actions and Sequences**~~ done (P2): View, Edit, Deselect all, type styling, add to sequence, sequence editing buttons, rename, console, reconnect → Actions.
3. ~~**History, Formulas, Code generation, Watch, Logging**~~ done (P2).
4. ~~**Read-all progress**, favorites sort, tooltips, Ctrl+K palette~~ done (P2).
5. ~~**Settings additions**: export/import/clear, About, System info, Hardware config~~ done (P3).
6. ~~**Sessions**~~ done (P3).
7. Planned pages, as in the frontend plan. ~~Dumps (§12)~~, ~~Radio Calculator diff (§21)~~ and ~~Radio and PHY (§23, §24)~~ done.

Each batch adds tests tagged with the `req` IDs, so the coverage report (P2) shows progress against this list.
