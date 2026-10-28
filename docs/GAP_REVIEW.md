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
| Test execution | §33 | ⏸ Deferred (decided 2026-10-28; see docs/API_DESIGN.md §11.4) |

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
| 15 | ✅ Custom functions | Done on the Advanced page: list with New / Rename / Delete (names must be Python identifiers, since the result is stored as `result_<name>`), editor with live highlighting and line numbers, saves as you type to `~/.sirat_custom_functions.json`; Run (or Ctrl+Enter) in the console's session, so variables carry over both ways, with print output, result and traceback; top-level `return` works; one run at a time; Add to Actions (`custom_function` op), which sequences run with the code. |
| 19 | ✅ Memory viewer | Done: address (hex or decimal), size 1–4096, Bytes (8 + 8 with ASCII) / Words / DWords little-endian, header naming the aligned start; bytes that changed since the last read of the same block are highlighted; Copy dump in the req 19 text layout; click a row address to use it for a write; Byte / Word / DWord write always confirmed, then the block re-reads; last address in `~/.sirat/memory_viewer.json` (also in settings export). |
| 20 | ✅ Python console | Done: one station session per DUT (opened on first use, ended on disconnect or position change, Restart session clears it), auto eval/exec, colored output (input, stdout, result, error, notes), multi-line input with Shift+Enter, ↑ / ↓ history with wraparound, Help (and typing `help`) lists the namespace, examples and keys. History isn't saved (req 20). |
| 22 | ✅ DUT control API explorer | Done: Common / Host / LPW / WiFi tree with filter and Collapse all; signature and docstring; parameter form (True/False switch for bool, defaults pre-filled, empty or unchanged fields use the method's default, str parameters keep what was typed); Execute with result type and text; hints for RPC timeout, RPC transport and RAIL assert; Add to Actions (`dut_control_method`, req 22 format), which sequences run. |
| 23 | ✅ PHY loaders | LPW and WiFi parameters, packet structure preview, add to Actions. Done on the Radio and PHY page: LPW PHY by name, known list or file, success prompt offering Add to Actions; WiFi form with every §23 option (band-aware channels, standard-aware power modes and rates, TX and 11ax/be advanced sections), live packet diagram with airtime, success dialog with config, function and TestInputs overrides; WiFi only on Everest chips (`--scenario everest` to try it). Needs `docs/API_CHANGE_phy_and_prs.md`. Assumptions: MP power only for ax/be; 2.4 GHz bandwidth up to 40 MHz. |
| 24 | ✅ PRS routing | Signal/pin/channel, port and channel validation, active routes, add to Actions. Done: family signals via `rf.prs_signals` (fallback list if unavailable), categories, live A/B vs C/D hint plus the §24 warning on Apply, routes table with Remove (records the six register writes in History), routes cleared on disconnect. |
| 25–27 | ✅ Signal generator, BLE packet, GFSK | Done on the Instruments page: instrument status with Connect after a drop; type, waveform (Reload rescans the files), frequency in MHz, power, overrides as KEY=value; Apply, Load from instrument, Infinite/Single trigger, RF off/on; Add to Actions in the §25 format plus the instrument id; code. Settings in `~/.sirat/signal_generator.json`. BLE packet: AA, CRC init, whitening, preamble, derived sync word, code window with Copy/Save, `~/.sirat/ble_packet.json`. GFSK: symbol rate, deviation (shows h), BT, frequency, power, payload; code and `gfsk_packet` actions. Assumptions: the sync word is the AA in on-air bit order; generated code imports `packet_generator` (library name to confirm). |
| 28 | ✅ RF switch | Done: paths from `rf.paths`, DUT position 1–4, Connect path / Disconnect, current path from the `rf_path` fact, Add to Actions (§28 format). |
| 29 | ✅ Temperature chamber | Done: large live reading with Stable/Heating/Cooling and a trend line, polled at the chosen interval only while the page shows; Set temperature; Wait for stable (tolerance, hold time) as an abortable activity. Nothing saved (§29). |
| 30 | ✅ ECA capture | Done: channels, trigger, edge, sample rate, duration, pre-trigger with a sample-count limit; abortable capture; paged download; one plot per channel with linked drag-to-zoom, trigger line and markers A/B (Δt and 1/Δt); per-channel range, mean, rising edges, frequency, high time, first rise; Save CSV with a metadata header. |
| 33 | Test execution | Deferred: not in v1 (docs/API_DESIGN.md §11.4) |

---

## Suggested order

1. ~~**P1 batch**~~ done (one sitting): formula file format, sequence semantics (skip disabled, warn on missing, per-action steps), formula formatting and `pow`, History field-write display, watch format. Item 8 (log files) waits for your decision.
2. ~~**Actions and Sequences**~~ done (P2): View, Edit, Deselect all, type styling, add to sequence, sequence editing buttons, rename, console, reconnect → Actions.
3. ~~**History, Formulas, Code generation, Watch, Logging**~~ done (P2).
4. ~~**Read-all progress**, favorites sort, tooltips, Ctrl+K palette~~ done (P2).
5. ~~**Settings additions**: export/import/clear, About, System info, Hardware config~~ done (P3).
6. ~~**Sessions**~~ done (P3).
7. Planned pages, as in the frontend plan. ~~Dumps (§12)~~, ~~Radio Calculator diff (§21)~~, ~~Radio and PHY (§23, §24)~~, ~~Instruments (§25–§30)~~ and ~~Advanced (§15, §19, §20, §22)~~ done. Only the Tests page (§33) is left, and it is deferred.

Each batch adds tests tagged with the `req` IDs, so the coverage report (P2) shows progress against this list.
