---
target: SiRAT main window
total_score: 24
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
target_fingerprint: "sha256:4f5b1bc040c5b39e981f45e8949d053ade585fb10679f15ac8831b8d9021c943"
target_path: "C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
timestamp: 2026-10-28T06-48-49Z
slug: src-sirat-ui-qml-main-qml
---
Method: design review only (detector not applicable: QML desktop app; `impeccable detect` reads web markup and returned [] for src/sirat_ui/qml)

Target: the whole SiRAT main window (src/sirat_ui/qml/Main.qml and its pages). Mode: Operate. Reviewed from fresh off-screen renders of Registers, Watch and logger, Sequences, Actions, Dumps with the Radio Calculator diff, the critical-write confirmation, disconnect recovery, and dark mode.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Strong connection/PHY pills and sequence progress; the status bar carries activity in 10px muted text |
| 2 | Match System / Real World | 3 | Correct domain language for experts; a few labels are ambiguous ("Read / Write" in History reads as actions but filters) |
| 3 | User Control and Freedom | 2 | No way to undo or revert a register write; "Delete all" sits right next to "Delete" |
| 4 | Consistency and Standards | 2 | Register names are sans in the tree and mono everywhere else; checked checkboxes render pink like an error |
| 5 | Error Prevention | 3 | Critical-write confirmation, buttons gated by requires, PRS check; destructive buttons placed next to safe ones |
| 6 | Recognition Rather Than Recall | 2 | Icon-only nav rail (9 faint line icons) and icon-only toolbar buttons (eye, pencil, {}, copy, trash) |
| 7 | Flexibility and Efficiency | 2 | Ctrl+K palette and pop-outs are good; only 2 shortcuts exist, none for Read / Write / Run |
| 8 | Aesthetic and Minimalist Design | 2 | The always-on dock takes ~28% of the height and duplicates the Actions page; two black primaries per screen |
| 9 | Error Recovery | 3 | The recovery dialog names the cause, what was cleared, and the next steps |
| 10 | Help and Documentation | 2 | Inline hints and "?" tips exist; no help reference or shortcut list |
| **Total** | | **24/40** | **Acceptable** |

## Design Specificity Verdict

**LLM assessment.** The register surfaces are authored for this product: the 32-cell bit pattern grouped by byte, the field table with enum, notes and watch/log toggles inline, the chip label, and actions color-coded by operation kind. A generic admin template wouldn't have these. Around them, the shell is category-standard: equal-weight white cards on an off-white canvas, a thin icon rail, and black buttons as the only emphasis. Fine for Operate, but the frame doesn't help the expert read state at a glance. Hierarchy comes from card boundaries, not from what matters on the bench (the live value, the DUT state, the running activity).

**Deterministic scan.** Not applicable: the detector only reads web markup and returned an empty result for the QML tree. That empty result is not a clean bill.

**Visual overlays.** None; there's no browser page to inject into.

## Overall Impression

A capable, careful engineering tool with genuinely good safety moments. The biggest opportunity is the frame, not the pages: a permanent bottom dock and competing primaries spend the expert's attention and screen height on things that aren't the current task.

## What's Working

1. **Register detail is fast and specific.** Value, format toggle, Read/Write, a clickable bit grid, and a field table with enums, notes and watch/log toggles: the whole loop from seeing a value to changing it fits in one view.
2. **Safety moments are well designed.** The critical-write dialog shows register, address, current and new value with Cancel as the safe default. The disconnect dialog names the cause and what was cleared, and offers Reconnect, PHY reload and "Add to Actions" in one place.
3. **State is always on screen.** Connection and PHY pills in the top bar, DUT position switcher, sequence progress with the running action highlighted, and an activity readout in the status bar.

## Priority Issues

**[P1] The permanent bottom dock costs a quarter of the screen and duplicates pages**
- **Why it matters:** History, Actions and Log sit under every page at ~28% of the height. On the Actions page the action list appears twice; on Sequences the page console and the Log show the same events. The watch list and logger, the screens engineers stare at during a run, lose the most room.
- **Fix:** Make the dock collapsible to a one-line strip (latest log line, last history entry, activity) and remember its state per page. Hide the dock's Actions panel on the Actions page. Default it collapsed on Watch and Sequences.
- **Suggested command:** /impeccable distill

**[P1] Muted text fails contrast where engineers read numbers**
- **Why it matters:** `textMuted` is #8A8A86 on white, about 3.5:1, used at 10–11px for addresses, table headers, helper text and the status bar. Addresses and reset values are data, not decoration, and the AA bar for text this small is 4.5:1.
- **Fix:** Darken `textMuted` to about #6B6B67 (≈5.3:1) in light mode, check the dark value against #1A1B1E, and stop using muted for data columns (addresses, reset values).
- **Suggested command:** /impeccable audit

**[P1] Two primary buttons compete on most screens**
- **Why it matters:** The dock's "Run checked" is solid black on every page, so it's as loud as Write on Registers, Take a dump on Dumps, and Add all to logger on Watch. The eye lands on the wrong action, and on Registers the two most consequential buttons look alike.
- **Fix:** One primary per page. Make the dock's Run checked a secondary button; keep black for the page's main action.
- **Suggested command:** /impeccable quieter

**[P2] Icons stand in for labels, and there are almost no shortcuts**
- **Why it matters:** The nav rail has 9 similar line icons at low contrast with labels only in hover tooltips. The dock and Actions headers use icon-only buttons (eye, pencil, {}, copy, trash). Experts end up hovering to find things. Only Ctrl+K and Ctrl+Q exist, and nothing reads or writes the selected register from the keyboard.
- **Fix:** Add short labels under the rail icons, or an expandable rail. Label "{}" as "Code". Add shortcuts for Read (F5), Write (Ctrl+Enter), Run checked, Toggle live, and page switching (Ctrl+1…9), and list them in the palette.
- **Suggested command:** /impeccable clarify

**[P2] Status color is applied to whole rows**
- **Why it matters:** The Radio Calculator diff floods every row red, amber or green, so the table reads as a color block and the values lose contrast, especially in dark mode with saturated maroon and olive fills. Checked checkboxes in Actions use the same pink as errors.
- **Fix:** Color only the Status cell (or a 3px left marker) and keep row backgrounds neutral. Give checkboxes a neutral or accent check color.
- **Suggested command:** /impeccable quieter

## Persona Red Flags

**Alex (Power User):** No key for Read or Write on the selected register; writing means clicking into the field, typing, then reaching for the Write button. Run checked has no shortcut. Page switching is click-only apart from the palette. The dock can't be hidden to make room.

**Sam (Accessibility):** No `Accessible` names on any QML item (0 in the tree), so icon-only buttons announce nothing. Muted text at 10–11px is 3.5:1. Diff status relies on color plus emoji glyphs.

**Priya (RF validation engineer, at the bench):** Glances at the screen from a step back while adjusting instruments. Live watch values are 13px mono in a table that the dock squeezes. The summary she needs ("4 mismatches") is the same size as the rows. Recording state in the logger is a small chip in the corner.

## Minor Observations

- The register header puts the chip family ("LION A0") in bold, larger than the register name, though the chip is already in the top bar.
- Dumps show the full temp folder path truncated in the card header; the path belongs in a tooltip or Settings.
- The History toolbar mixes filter toggles (Read/Write) with actions (Run, Create action, code, copy, delete) in one row with no divider.
- "refresh every (s)" is separated from its input by the header; the label reads as a subtitle.
- The Radio summary mixes emoji glyphs (✓ ⚠ ❌) with the app's line icons.
- The status bar is 10px and easy to miss, though it carries "Activity executing".

## Questions to Consider

- What if the dock were a status strip that expands on demand, so every page got its full height back?
- Should the live value be the largest thing on the Registers and Watch screens, rather than the card titles?
- What would the app look like with exactly one solid button per page?
- Could the nav rail show the DUT's state (connected, PHY, running) instead of only page icons?
