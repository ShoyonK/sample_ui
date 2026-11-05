# Chaos testing strategy

**Date:** 2026-11-05
**Scope:** what can go wrong in the SiRAT frontend that the tests don't cover yet, and how we'll test it.

The app talks to a station that can drop a DUT, lose an instrument, time out, restart or send events late. The
fake backend (`gateway/fake/`) can already simulate some of this. This document lists what's covered, what isn't,
and a plan in three phases. **All three phases are done (2026-11-05).** What's left is in Open questions.

Legend:

| Mark | Meaning |
|---|---|
| ✅ | Fixed in phase 1, with tests |
| 🔴 | Confirmed: reproduced on 2026-11-05 |
| 🟠 | Not tested; likely to hurt the user |
| 🟡 | Not tested; lower risk or later |

---

## Covered today

| Fault | Where it's tested |
|---|---|
| DUT drops during a read, the watch list, a console session, PRS routes, a test run | `tests/integration/test_connection_and_state.py`, `tests/unit/domains/` |
| Connect fails; the Connect button stays usable | `test_connection_and_state.py` |
| Only one recovery dialog at a time | `test_connection_and_state.py` |
| Hardware error during a run faults the position; Recover clears it | `test_fault_recovery.py` |
| Writes refused while a sequence runs | `test_connection_and_state.py` |
| A call times out and finishes late (`call.late`) | `test_api_rev2.py`, `test_fake_station.py` |
| Corrupt or invalid settings files are cleaned and reported | `tests/unit/stores/test_schemas.py` |
| Runaway console code is stopped | `test_advanced.py` |
| Any QML warning fails an end-to-end test | `tests/e2e/conftest.py` |

Settings files are saved atomically (`stores/json_store.py` writes a temporary file, then renames it), so a crash
mid-save can't leave a half-written file.

Fault switches the fake has: `fail_next`, `time_out_next`, `set_latency`, `drop_dut`, `drop_instrument`,
`auto_resolve` / `release`, `drop_after_reads`, `unreachable_hosts`, `advanced.exec_time_limit_s`,
`station_tests.outcomes`, and from phase 1 `restart_station`, `swallow_next`, `duplicate_next`.

---

## Gaps

### 1. Things that crash or report the wrong result (fix first)

| | Gap | What happens |
|---|---|---|
| ✅ | **No crash safety net.** | Fixed: `app/crash_guard.py` logs the traceback to the session log, shows an error toast and keeps SiRAT running. Installed by `sirat` / `python -m sirat_ui` only, so pytest-qt still fails a test on an exception. |
| ✅ | **The fake ignored a DUT drop during a sequence.** | Fixed: the fake's sequencer ends the run with `dut_disconnected`, and the Sequences page shows Failed with "DUT 1 disconnected". |
| ✅ | **Saving can fail** (full disk, denied permission, file locked). | Fixed: `JsonStore.save` reports to the app, which shows "Couldn't save <file>: <reason>" and logs it; the change stays on screen and the next save tries again. Exports: every one already said "Couldn't…" except ECA Save CSV, fixed in phase 2. |
| ✅ | **DUT drops mid-operation**: action runs, dumps, the radio diff, Read all registers, custom functions, memory reads, the data logger. | Tested: each stops, says why, and saves nothing partial (a dump says "Dump stopped … Nothing was saved"). No app changes were needed. |
| ✅ | **An instrument drops mid-activity**: a chamber wait or an ECA capture. | Tested: both end with "… disconnected" (the ECA test already existed). |
| 🟠 | **No watchdog.** If `activity.finished` never arrives, nothing notices. | The page shows Running forever; only Stop gets out. Waiting on open question 1; `test_a_lost_finished_event_does_not_leave_the_page_running` is marked as an expected failure until then. |

### 2. Timing and ordering

| | Gap |
|---|---|
| ✅ | **Switching DUT position mid-operation.** Found and fixed: a dump and Read all carried on reading from the new DUT and saved a mix of both; the watch list kept showing DUT 1's values. Now switching stops the watch list and logger (with a toast), stops a dump, radio diff or Read all ("stopped: you switched to DUT 2", nothing saved), clears cached values, and ignores a read that returns from the old DUT. Sequences and test runs carry on on their own DUT. |
| 🟡 | **Late replies**: after switching DUT and after leaving the page are tested. After a pop-out closed and after a reconnect are not yet. |
| ✅ | **Odd events**: a duplicated `activity.finished` finishes once; events for an unknown activity are ignored; a drop on a DUT you aren't viewing opens its recovery dialog. A lost `activity.finished` is the watchdog gap above. |
| ✅ | **Double clicks.** Found and fixed: a second Run on a sequence started a second run that the station refused, and the page lost track of the first; a second Run on an action failed with an error. Run is now ignored while a run is going. |

### 3. The station service itself

The fake has no switch for these, and the real client (`gateway/api/`) isn't written yet. They become urgent
when it is.

| | Gap |
|---|---|
| ✅ | The service restarts (`restart_station`): runs end with "Station service restarted", the watch list stops, the recovery dialog opens, and Reconnect falls back to a full connect because the bench setup is gone. The service *disappearing* needs the real client. |
| 🟡 | `release_id` changes, or the protocol version doesn't match, at `sys.hello`. |
| 🟡 | Events are lost while reconnecting. |

### 4. Files and environment

| | Gap |
|---|---|
| ✅ | Saving fails: settings files (phase 1); History, Log and Settings exports and ECA Save CSV are tested (ECA was fixed). |
| 🟡 | `C:\temp\sirat` isn't writable, so there's no session log. |
| 🟡 | Two copies of SiRAT open at once, writing the same `~/.sirat*` files. |
| 🟡 | Closing the app while something runs: tested that it closes cleanly and auto-saves; the run carries on on the station. Whether to abort it is open question 2. |

### 5. Scale and long sessions

| | Gap |
|---|---|
| 🟡 | A console or custom function that prints a flood of output. |
| 🟡 | Very large dumps and register maps; very long names. |
| 🟡 | Memory growth over a day-long session (logs are capped at 2,000 lines and consoles at 400; check the rest). |
| 🟡 | Timers left running, for example chamber polling after its pop-out closes. |

---

## Plan

### Phase 1: a safety net and an honest fake ✅ done 2026-11-05

1. **Global error handler** (`app/application.py`): install `sys.excepthook` so an unhandled exception is logged
   with its traceback, shown as an error toast, and the app keeps running. A test raises inside a slot and checks
   the app is still alive.
2. **Saves that fail visibly**: `JsonStore.save` failures become a toast ("Couldn't save favorites: …") and a log
   line, and the in-memory state stays as the user left it.
3. **The fake ends activities on a drop**: the sequencer, bench activities (chamber wait, ECA capture) and test
   runs finish with `dut_disconnected` / `instrument_error` when their DUT or instrument goes away, like the real
   service.
4. **New fake switches**: `restart_station()`, `swallow_next(event_type)`, `duplicate_next(event_type)`.
   Failing saves are simulated in tests by making `os.replace` raise, so no switch was needed.

Tests: `tests/unit/test_crash_guard.py`, the phase 1 block in `tests/unit/domains/test_fault_recovery.py`, and the
fake's new switches in `tests/unit/gateway/test_fake_station.py`.

### Phase 2: one targeted test per gap ✅ done 2026-11-05

`tests/integration/test_chaos.py`, 24 tests. Bugs it found, all fixed: a DUT switch mixing two DUTs in a dump or
Read all, the watch list staying on the old DUT, double-clicked Run on sequences and actions, ECA Save CSV
failing silently, Hardware configuration logging "saved" after a failed write, and the fake keeping a bench setup
across a restart. Still open: late replies after a pop-out closes or a reconnect, the watchdog (question 1).

Each test injects one fault at one moment and checks three things: the user is told what happened, nothing is
left looking busy, and the next action works. In order:

1. DUT drop mid: action run, sequence, dump, radio diff, Read all, custom function, memory read, logger recording.
2. Instrument drop mid: chamber wait, ECA capture.
3. Position switch mid: sequence, watch, logger, test run, Read all.
4. Save fails for each settings file, and for each export.
5. Late reply after: leaving the page, closing the pop-out, reconnecting.
6. Station restart: positions reset, the tree reloads, nothing stays busy.
7. Odd events: duplicates, unknown ids, other positions.
8. Close the app during a run.

### Phase 3: a seeded chaos runner ✅ done 2026-11-05

`tests/chaos_runner.py` plays random user steps (read, write, run sequences and actions, watch, logger, switch
DUT, connect and reconnect, dumps, Read all, radio diff, tests, custom functions, memory, chamber, ECA,
favorites, pop-out windows) with faults mixed in at random (DUT and instrument drops, station restarts, failing
calls, timeouts, slow calls, duplicated events). Everything comes from one seed, so a failure replays exactly.

- **Checked at every step**: whatever the station is running, the app shows as running (a sequence or actions,
  tests, a chamber wait, an ECA capture); a DUT drop, instrument drop or restart leaves a warning or error in the
  log at once; nothing raises out of a step (that would have been a crash).
- **Checked every 8 steps, once everything has settled**: nothing shows busy while the station is idle; Run
  buttons match the station's facts (`core/requires.py`); every `~/.sirat*` file is valid JSON.
- **Two variants**: against the ViewModels (fast: 500 seeds of 300 steps take about 2.5 minutes), and against the
  real window (`test_chaos_with_the_real_window`), where any QML warning fails it. The real-window variant skips
  the radio diff, because it opens Windows' own file dialog.
- **Left out**: losing an `activity.finished` (the watchdog, open question 1).
- **How to run** (marked `chaos`, so the normal run leaves it out; a 60-step smoke run stays in the normal suite):

  ```
  uv run pytest -m chaos                                        # 25 seeds, both variants
  uv run pytest -m chaos --chaos-seed 7                         # replay one seed
  uv run pytest -m chaos --chaos-seeds 500 --chaos-steps 300    # the nightly run
  ```

Bugs it found, all fixed, each with a regression test:

1. A dialog reopened during its closing animation stayed closed while its ViewModel thought it was open, so
   clicking again did nothing. Dialogs now bind `shown` instead of `visible`, and reopen if they finish closing
   while they should be open.
2. A dialog open in a pop-out that closed stayed in the hidden window: modal, but out of sight. It now moves to the
   main window.
3. A closed pop-out stayed visible until Qt destroyed it, so dialogs could still open in it. It now hides at once.

The every-step check was added after a test of the runner itself: with the double-click fix from phase 2 taken
out, the settled checks alone missed it; with the every-step check it failed on 13 of 40 seeds.

---

## Open questions

1. What should the app do with an activity that never finishes: a timeout per activity type, or only a visible
   "no news for N seconds" hint?
2. On closing the app mid-run, should it abort the activity, ask first, or leave it running on the station?
3. Should two SiRAT copies on one PC be prevented (a lock file), or allowed with a warning?
