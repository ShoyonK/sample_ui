---
target: SiRAT main window
total_score: 29
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 0
target_identity: "file:C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
target_fingerprint: "sha256:32055e7ad9d2c1fc131e79f91a78ea6cef676d7d24d9cc6b365df13f4702c4ff"
target_path: "C:\\Users\\shoyo\\PythonProjects\\Sample_UI\\src\\sirat_ui\\qml\\Main.qml"
timestamp: 2026-10-28T07-34-35Z
slug: src-sirat-ui-qml-main-qml
---
Method: design review only (detector not applicable: QML desktop app; `impeccable detect` reads web markup and returned [] for src/sirat_ui/qml)

Target: the SiRAT main window (src/sirat_ui/qml/Main.qml and its pages), third run, after the Watch toolbar and accessibility fixes. Mode: Operate. Ignored per .impeccable/critique/ignore.md: register-write undo.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Strip, pills and progress are solid; Watch's Live state is now a gray segment, weaker than the green pill it replaced |
| 2 | Match System / Real World | 3 | Domain language is right; History's "Read / Write" filter still reads like actions |
| 3 | User Control and Freedom | 3 | Cancel, Abort, Esc, dock hide, confirmed Delete all (write undo excluded by request) |
| 4 | Consistency and Standards | 3 | Register names still sans in the tree, mono elsewhere |
| 5 | Error Prevention | 3 | Critical-write confirmation, gated buttons, confirmed bulk deletes |
| 6 | Recognition Rather Than Recall | 3 | Labeled rail and buttons; shortcuts visible only in the palette |
| 7 | Flexibility and Efficiency | 3 | 13 shortcuts, collapsible dock, palette, pop-outs, keyboard focus through the window |
| 8 | Aesthetic and Minimalist Design | 3 | Watch toolbar now shows only what applies; the logger's stat tiles are still template filler |
| 9 | Error Recovery | 3 | Recovery dialog names cause, what was cleared, next steps |
| 10 | Help and Documentation | 2 | Inline hints, "?" tips, palette key hints; no help reference |
| **Total** | | **29/40** | **Good** |

## Design Specificity Verdict

**LLM assessment.** Coherent and specific to the job. What's left is precision, not structure: one state indicator lost its signal, one typographic rule isn't applied everywhere, and the Watch screen still doesn't use its height for the thing the bench engineer watches.

**Deterministic scan.** Not applicable (QML); the empty result isn't a clean bill.

**Visual overlays.** None.

## Overall Impression

Good, and close to done for an Operate surface. No P1 or P2 issues remain; everything below is P3 polish.

## What's Working

1. The Watch toolbar shows what applies now: rate, Live | Paused, Refresh, and selection actions only when rows are selected.
2. Every visible control has a screen-reader name, enforced by a test, and keyboard focus shows a clear ring.
3. One primary per page, calm status color, and a dock that gives the page its height back.

## Priority Issues

**[P3] Live lost its color**
- **Why it matters:** The lit "Live" segment is the same gray as any selected segment, so at a glance Live and Paused look alike. The green pill it replaced was the clearest signal on the page.
- **Fix:** Light the Live segment in the ok tone (okBg fill, okFg text, a small dot) and Paused in neutral.
- **Suggested command:** /impeccable colorize

**[P3] Shortcuts aren't shown where they're used**
- **Why it matters:** F5 and Ctrl+R live only in the palette.
- **Fix:** Append the key to the Read and Run checked tooltips from the shortcut table.
- **Suggested command:** /impeccable clarify

**[P3] Register names switch type; the chip outweighs the register**
- **Why it matters:** Sans in the tree, mono everywhere else; "LION A0" is larger than the register name.
- **Fix:** Mono in the tree; drop the chip line to secondary weight.
- **Suggested command:** /impeccable typeset

**[P3] The logger's stat tiles are filler**
- **Why it matters:** "Fields 2" and "Samples 8" take a row of big tiles to say what the status line under them already says.
- **Fix:** Remove the two tiles, keep the status line, move Sample rate into the header next to Recording.
- **Suggested command:** /impeccable distill

**[P3] Watch doesn't use its height for the values**
- **Why it matters:** Six rows fill a third of the panel; live values stay 13px while the engineer reads them from a step back.
- **Fix:** Let rows grow with the panel up to a larger value size, or offer a compact/large density toggle that enlarges Value and Calculated.
- **Suggested command:** /impeccable layout

## Persona Red Flags

**Alex (Power User):** Keyboard covers the main loop; shortcuts still found only via the palette.

**Sam (Accessibility):** Names and focus rings are in. Not yet verified with a real screen reader (NVDA).

**Priya (RF validation engineer):** Live vs Paused is harder to read than before; values are small on a mostly empty panel.

## Minor Observations

- The Dumps header still shows a truncated temp folder path.
- History's toolbar mixes filter toggles with actions.
- The status bar is 10px.
- The screenshot script's "registers_dark" capture shows the Dumps page.

## Questions to Consider

- Should Watch have a "bench" density with big values?
- Is a help page with the shortcut list worth adding to Settings?
