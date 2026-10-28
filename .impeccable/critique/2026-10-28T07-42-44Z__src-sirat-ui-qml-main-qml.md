---
target: SiRAT main window
total_score: 30
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 0
target_identity: "file:C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
target_fingerprint: "sha256:32055e7ad9d2c1fc131e79f91a78ea6cef676d7d24d9cc6b365df13f4702c4ff"
target_path: "C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
timestamp: 2026-10-28T07-42-44Z
slug: src-sirat-ui-qml-main-qml
---
Method: design review only (detector not applicable: QML desktop app; `impeccable detect` reads web markup and returned [] for src/sirat_ui/qml)

Target: the SiRAT main window (src/sirat_ui/qml/Main.qml and its pages), fourth run, after the five P3 fixes. Mode: Operate. Ignored per .impeccable/critique/ignore.md: register-write undo.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Live is green again, strip and pills are clear; the status bar is still 10px |
| 2 | Match System / Real World | 3 | History's "Read / Write" filter still reads like actions |
| 3 | User Control and Freedom | 3 | Cancel, Abort, Esc, dock hide, confirmed bulk deletes (write undo excluded) |
| 4 | Consistency and Standards | 3 | Register comparison rows still flood red while the Radio diff colors only the status |
| 5 | Error Prevention | 3 | Critical-write confirmation, gated buttons, confirmed bulk deletes |
| 6 | Recognition Rather Than Recall | 3 | Labels, shortcut tooltips, palette; a handful of icon-only toolbar buttons remain |
| 7 | Flexibility and Efficiency | 4 | Shortcuts, palette, pop-outs, density, collapsible dock, bulk selection |
| 8 | Aesthetic and Minimalist Design | 3 | The Watch header is back to 7 controls (10 with a selection) after the density switch |
| 9 | Error Recovery | 3 | Recovery dialog names cause, what was cleared, next steps |
| 10 | Help and Documentation | 2 | Tooltips and palette hints, but no place that lists the shortcuts or explains the pages |
| **Total** | | **30/40** | **Good** |

## Design Specificity Verdict

**LLM assessment.** Specific to the bench and consistent in most places. Large density on Watch is the strongest new move: values now read from a step back, which no generic table does. Remaining work is consistency (one diff still uses the old row flood) and a small help surface.

**Deterministic scan.** Not applicable (QML); the empty result isn't a clean bill.

**Visual overlays.** None.

## Overall Impression

Good, with nothing above P3. The app now behaves like a tool built for its users; the remaining items are consistency and a help surface.

## What's Working

1. Watch's Large density turns the page into a bench readout, remembered across launches.
2. Shortcuts are taught where they're used (tooltips) and listed where experts look (palette), from one table.
3. Type and emphasis follow one system: mono for register names everywhere, one primary per page, color only where it carries meaning.

## Priority Issues

**[P3] Register comparison still floods changed rows red**
- **Why it matters:** The dump comparison tints the whole changed row pink while the Radio diff now colors only the status. Same kind of result, two visual rules; the pink row also lowers contrast on the Before value.
- **Fix:** Keep rows neutral; show the change with the After value in the danger tone (already done) and a small marker in the Change cell, matching the Radio diff.
- **Suggested command:** /impeccable quieter

**[P3] The Watch header is crowded again**
- **Why it matters:** Rate, Live | Paused, Refresh once, Compact | Large, Add all to logger, clear and pop-out sit in one row, plus three more with a selection. Density is set once and rarely changed, yet it takes prime space.
- **Fix:** Move Compact | Large to the right end as a small icon toggle (or into a "View" menu with pop-out), keeping the left side for what changes during a run.
- **Suggested command:** /impeccable distill

**[P3] No place lists the shortcuts or explains the pages**
- **Why it matters:** Shortcuts are discoverable one at a time, but there's no overview, and a new engineer has no "what is this page for".
- **Fix:** Add a "Keyboard shortcuts" section to Settings (generated from the shortcut table), and a one-line description under each page title in the palette's page entries.
- **Suggested command:** /impeccable onboard

**[P3] History's toolbar mixes filters with actions**
- **Why it matters:** "Read | Write" filter toggles sit in the same row and style as Run, Create action and Code, so they read as commands.
- **Fix:** Label the filter ("Show: Read · Write") or move it into the list header, and keep actions on the right.
- **Suggested command:** /impeccable clarify

## Persona Red Flags

**Alex (Power User):** Nothing blocking. Would like a shortcut overview.

**Sam (Accessibility):** Names and focus are in; still unverified with NVDA.

**Priya (RF validation engineer):** Large density solves reading values from the bench. The Watch header crowding costs her a moment finding Live.

## Minor Observations

- The Dumps header still shows a truncated temp folder path.
- The status bar is 10px.
- The screenshot script's "registers_dark" capture shows the Dumps page.

## Questions to Consider

- Should the Watch header split into "run" controls on the left and "view" controls on the right?
- Would a first-run tip in the palette ("Press Ctrl+K anywhere") be enough onboarding for experts?
