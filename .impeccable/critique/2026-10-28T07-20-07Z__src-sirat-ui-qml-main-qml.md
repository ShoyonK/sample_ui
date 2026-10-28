---
target: SiRAT main window
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 0
target_identity: "file:C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
target_fingerprint: "sha256:32055e7ad9d2c1fc131e79f91a78ea6cef676d7d24d9cc6b365df13f4702c4ff"
target_path: "C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
timestamp: 2026-10-28T07-20-07Z
slug: src-sirat-ui-qml-main-qml
---
Method: design review only (detector not applicable: QML desktop app; `impeccable detect` reads web markup and returned [] for src/sirat_ui/qml)

Target: the SiRAT main window (src/sirat_ui/qml/Main.qml and its pages), re-run after the dock, contrast, primary-button, label, shortcut and status-color fixes. Mode: Operate. Reviewed from fresh renders of Registers, Watch and logger, Sequences, Actions, Dumps with the Radio Calculator diff, the command palette, and dark mode.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | The collapsed strip keeps the last write, checked count and newest log line on screen; the status bar is still 10px |
| 2 | Match System / Real World | 3 | Domain language is right; History's "Read / Write" still reads as actions but filters |
| 3 | User Control and Freedom | 2 | Still no way to revert a register write; "Delete all" still sits next to "Delete" |
| 4 | Consistency and Standards | 3 | Neutral checkboxes and labeled buttons fixed the worst mismatches; register names are still sans in the tree, mono elsewhere |
| 5 | Error Prevention | 3 | Critical-write confirmation and state-gated buttons; destructive buttons still adjacent |
| 6 | Recognition Rather Than Recall | 3 | Labeled nav rail and View/Edit/Code; shortcuts show in the palette but not on the buttons they trigger |
| 7 | Flexibility and Efficiency | 3 | 13 shortcuts, a collapsible dock, palette, pop-outs |
| 8 | Aesthetic and Minimalist Design | 3 | One primary per page and a strip instead of a permanent dock; the Watch toolbar still crowds 9 controls into one row |
| 9 | Error Recovery | 3 | The recovery dialog names the cause, what was cleared and the next steps |
| 10 | Help and Documentation | 2 | Inline hints, "?" tips and palette key hints; no help reference |
| **Total** | | **28/40** | **Good** |

## Design Specificity Verdict

**LLM assessment.** The frame now serves the work. The strip says what happened without taking a quarter of the screen, the labeled rail reads at a glance, and the Radio diff reads as data with color only where the verdict is. The register surfaces (bit grid, field table with notes and enums) remain the most product-specific parts. The remaining generic note is the data logger's stat tiles (big "2" and "8" with small labels): a dashboard template where a single status line would do.

**Deterministic scan.** Not applicable: the detector reads web markup and returned an empty result for the QML tree, which is not a clean bill.

**Visual overlays.** None; no browser page to inject into.

## Overall Impression

A clear step up, from Acceptable to Good. The three P1s are gone. What's left is depth rather than frame: undo for writes, the crowded Watch toolbar, and accessibility basics that no QML item has yet.

## What's Working

1. **The dock earns its space.** Collapsed on Watch and Sequences, open where you edit registers, remembered per page, and the strip still surfaces the last write and the newest log line.
2. **Emphasis is honest.** One solid button per page (Write on Registers, Take a dump on Dumps), muted text at 4.5:1 or better, and status color confined to the Status cell.
3. **Accelerators are discoverable.** Every shortcut lives in one table and shows as a key hint in the palette, so an expert can learn them from the place they already use.

## Priority Issues

**[P2] A register write can't be undone**
- **Why it matters:** History records every write with its value, but there's no way to put the previous value back. After a wrong write, the engineer has to find the old value and type it again, on a live DUT.
- **Fix:** Add "Revert" on the newest write in History (and in the strip's history segment): it writes the value read before the write, through the same confirmation and verification as any write. Record the pre-write value in the history entry.
- **Suggested command:** /impeccable harden

**[P2] The Watch toolbar packs 9 controls into one row**
- **Why it matters:** Refresh rate, Live, Pause, Refresh once, Delete selected, Add selected to logger, Add all to logger, trash and pop-out compete in one line. Live and Pause are two buttons for one state, and the selection actions show (disabled) even with nothing selected.
- **Fix:** Merge Live/Pause into one toggle next to the rate. Show selection actions only when rows are selected. Keep Add all to logger as the primary; move trash into the selection group.
- **Suggested command:** /impeccable distill

**[P2] Nothing is exposed to assistive technology**
- **Why it matters:** No QML item sets `Accessible.name` or `Accessible.role`, so the remaining icon-only buttons (copy, trash, save, erase, pop-out, hide) announce nothing, and tab order and focus rings are unverified.
- **Fix:** Give AppButton, IconButton and the nav buttons `Accessible.name` from their text or tooltip, and check keyboard focus order and visible focus on the main flows.
- **Suggested command:** /impeccable audit

**[P3] Shortcuts aren't shown where they're used**
- **Why it matters:** F5 and Ctrl+R are only discoverable through the palette. The Read button and Run checked don't mention them, so most users never learn them.
- **Fix:** Add the key to those buttons' tooltips ("Read · F5", "Run checked · Ctrl+R") from the same shortcut table.
- **Suggested command:** /impeccable clarify

**[P3] Register names switch type, and the chip outweighs the register**
- **Why it matters:** Register and field names are sans in the tree and mono everywhere else, and the detail header's bold "LION A0" is larger than the register name it sits beside.
- **Fix:** Use mono for register and field names in the tree too. Drop the chip line to secondary weight (the chip is already in the top bar).
- **Suggested command:** /impeccable typeset

## Persona Red Flags

**Alex (Power User):** Can now read, run, switch pages and hide the dock from the keyboard. Still no undo after a bad write, and the shortcuts are found only by opening the palette.

**Sam (Accessibility):** Contrast now passes. Still no accessible names on any control, so icon-only buttons are silent; focus visibility untested.

**Priya (RF validation engineer, at the bench):** Watch now has the full height, but the six rows use a third of it and the live values are still 13px. The logger's big stat tiles show counts she doesn't need while the values she does need stay small.

## Minor Observations

- The Dumps header still shows a truncated temp folder path.
- History's toolbar mixes filter toggles with actions in one row.
- The data logger's Fields / Samples tiles are the hero-metric template; one status line would do.
- The status bar is 10px.
- The screenshot script's "registers_dark" capture shows the Dumps page; it never navigates back to Registers.

## Questions to Consider

- Should Watch show live values large enough to read from the bench, with the table as the detail view?
- What would "undo" mean for a sequence run, not just one write?
- Could the strip's history segment carry the Revert action, so recovery is one click from anywhere?
