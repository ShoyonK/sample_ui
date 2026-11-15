"""The seeded chaos runner (docs/CHAOS_TESTING.md, phase 3).

Plays random user steps against the real container and fake station, with faults mixed in at random, and checks
the invariants every few steps once things have settled. Everything comes from one random.Random(seed), so a
failing seed replays exactly: `uv run pytest -m chaos --chaos-seed N`.

Faults left out on purpose: losing an `activity.finished` (no watchdog yet, open question 1).
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from sibench_ui.gateway.errors import ErrorCode
from sibench_ui.models.station import ActivityFinished, WatchValues
from support import Harness

SAMPLE_CFG = Path(__file__).resolve().parents[1] / "docs" / "samples" / "PHY_demo.cfg"
INSTRUMENTS = ["siggen1", "switch1", "chamber1", "eca1"]
PAGES = ["registers", "watch", "actions", "sequences", "dumps", "radio", "instruments", "advanced", "tests"]
FAILABLE = ["registers.read", "registers.write", "automation.seq.run", "dut.connect", "dut.reconnect",
            "memory.read", "tests.run", "instruments.chamber.wait_stable", "instruments.eca.capture"]
SETTLE_LIMIT_MS = 120_000


class ChaosFailure(AssertionError):
    pass


@dataclass
class Run:
    seed: int
    h: Harness
    rng: random.Random
    trail: List[str] = field(default_factory=list)   # what happened, for the failure report

    def fail(self, why: str) -> None:
        recent = "\n  ".join(self.trail[-25:])
        raise ChaosFailure(f"seed {self.seed}: {why}\nlast steps:\n  {recent}\n"
                           f"replay: uv run pytest -m chaos --chaos-seed {self.seed}")


# ---- user steps -----------------------------------------------------------------------------------

def _register(run: Run, writable: bool = False):
    regs = [r for p in run.h.services.catalog.peripherals for r in p.registers
            if (r.access.writable if writable else r.access.readable) and not r.read_sensitive]
    return run.rng.choice(regs) if regs else None


def read_register(run: Run) -> str:
    reg = _register(run)
    if reg:
        run.h.services.registers.read(reg)
    return f"read {reg.full_name if reg else '-'}"


def write_register(run: Run) -> str:
    reg = _register(run, writable=True)
    if reg and not reg.critical:
        run.h.services.registers.write(reg, run.rng.randint(0, min(reg.max_value, 0xFF)))
    return f"write {reg.full_name if reg else '-'}"


def run_sequence(run: Run) -> str:
    run.h.shell.sequences.run()
    return "run sequence"


def abort_sequence(run: Run) -> str:
    run.h.shell.sequences.abort()
    return "abort sequence"


def run_action(run: Run) -> str:
    names = list(run.h.services.actions.actions)
    if names:
        name = run.rng.choice(names)
        run.h.shell.actions.select_name(name)
        run.h.shell.actions.runCurrent()
        return f"run action {name}"
    return "run action -"


def toggle_watch(run: Run) -> str:
    run.h.shell.navigate("watch")
    run.h.shell.watch.toggleLive()
    return "toggle watch live"


def toggle_logger(run: Run) -> str:
    run.h.shell.navigate("watch")
    run.h.shell.logger.toggleRecording()
    return "toggle logger"


def navigate(run: Run) -> str:
    page = run.rng.choice(PAGES)
    run.h.shell.navigate(page)
    return f"go to {page}"


def switch_position(run: Run) -> str:
    position = run.rng.choice([1, 2])
    run.h.shell.state.setPosition(position)
    return f"switch to DUT {position}"


def connect(run: Run) -> str:
    position = run.h.state.position
    if run.h.shell.recovery.visible and run.rng.random() < 0.7:
        run.h.shell.recovery.reconnect()
        return "recovery: reconnect"
    run.h.services.connection.connect(position)
    return f"connect DUT {position}"


def take_dump(run: Run) -> str:
    peripherals = [p.name for p in run.h.services.catalog.peripherals]
    if not peripherals:
        return "dump -"
    name = run.rng.choice(peripherals)
    if run.rng.random() < 0.5:
        run.h.ix.answer_next({"name": f"chaos_{run.rng.randint(0, 999)}", "description": ""})
    run.h.shell.dumps.dumpPeripheral(name)
    run.h.shell.dumpPicker.startPicked()
    return f"dump {name}"


def read_all(run: Run) -> str:
    peripherals = run.h.services.catalog.peripherals
    if not peripherals:
        return "read all -"
    periph = run.rng.choice(peripherals)
    run.h.services.read_all.start(periph)
    return f"read all {periph.name}"


def radio_diff(run: Run) -> str:
    run.h.ix.answer_open(str(SAMPLE_CFG))
    run.h.shell.dumps.openRadioDiff()
    run.h.shell.dumpPicker.startPicked()
    return "radio diff"


def run_tests(run: Run) -> str:
    vm = run.h.shell.stationTests
    vm.ensureLoaded()
    for row in range(vm.catalogue.count):
        if run.rng.random() < 0.5:
            vm.toggle(row)
    vm.run()
    return "run tests"


def stop_tests(run: Run) -> str:
    run.h.shell.stationTests.stop()
    return "stop tests"


def custom_function(run: Run) -> str:
    functions = run.h.services.functions
    if not functions.names:
        functions.create("chaos_fn")
    run.h.shell.customFunctions.select(0)
    run.h.shell.customFunctions.run()
    return "run custom function"


def memory_read(run: Run) -> str:
    run.h.shell.memory.read()
    return "memory read"


def chamber_wait(run: Run) -> str:
    ch = run.h.shell.chamber
    ch.setField("target", str(run.rng.choice([20, 25, 40])))
    ch.setField("hold", "2")
    ch.setTemperature()
    ch.waitForStable()
    return "chamber wait"


def eca_capture(run: Run) -> str:
    run.h.shell.eca.capture()
    return "eca capture"


def toggle_favorite(run: Run) -> str:
    reg = _register(run)
    if reg:
        run.h.services.favorites.toggle(reg.full_name)
    return f"favorite {reg.full_name if reg else '-'}"


def pop_window(run: Run) -> str:
    windows = run.h.shell.windows
    if windows.openKeys and run.rng.random() < 0.5:
        key = run.rng.choice(list(windows.openKeys))
        windows.close(key)
        return f"close window {key}"
    kind, arg = run.rng.choice([("page", run.rng.choice(PAGES)), ("tool", "memory"), ("logger", "")])
    windows.open(kind, arg)
    return f"open window {kind}:{arg}"


STEPS: List[Tuple[Callable[[Run], str], int]] = [
    (read_register, 6), (write_register, 4), (run_sequence, 4), (abort_sequence, 1), (run_action, 4),
    (toggle_watch, 3), (toggle_logger, 3), (navigate, 4), (switch_position, 2), (connect, 4), (take_dump, 2),
    (read_all, 2), (radio_diff, 1), (run_tests, 2), (stop_tests, 1), (custom_function, 2), (memory_read, 2),
    (chamber_wait, 1), (eca_capture, 1), (toggle_favorite, 2), (pop_window, 2),
]


# ---- faults ---------------------------------------------------------------------------------------

def drop_dut(run: Run) -> str:
    position = run.rng.choice([1, 2])
    if run.h.fake.facts[position].dut_connected:
        run.h.fake.drop_dut(position)
        return f"FAULT drop DUT {position}"
    return "(no connected DUT to drop)"


def drop_instrument(run: Run) -> str:
    instrument = run.rng.choice(INSTRUMENTS)
    if run.h.fake.instruments[instrument].connected:
        run.h.fake.drop_instrument(instrument)
        return f"FAULT drop {instrument}"
    run.h.fake.bench.instruments[instrument].connected = True     # bring it back for later steps
    return f"(reconnected {instrument})"


def restart_station(run: Run) -> str:
    run.h.fake.restart_station()
    return "FAULT station restart"


def fail_next(run: Run) -> str:
    method = run.rng.choice(FAILABLE)
    code = run.rng.choice([ErrorCode.TIMEOUT, ErrorCode.INTERNAL, ErrorCode.HARDWARE_ERROR, ErrorCode.BUSY])
    run.h.fake.fail_next(method, code)
    return f"FAULT next {method} fails with {code.value}"


def time_out_next(run: Run) -> str:
    method = run.rng.choice(["registers.read", "registers.write", "memory.read"])
    run.h.fake.time_out_next(method, run.rng.choice([300, 1500, 4000]))
    return f"FAULT next {method} times out"


def slow_down(run: Run) -> str:
    method = run.rng.choice(["registers.read", "registers.read_many", "automation.seq.run", "tests.run"])
    ms = run.rng.choice([0, 50, 400])
    run.h.fake.set_latency(method, ms)
    return f"FAULT {method} latency {ms} ms"


def duplicate_event(run: Run) -> str:
    kind = run.rng.choice([ActivityFinished, WatchValues])
    run.h.fake.duplicate_next(kind)
    return f"FAULT next {kind.__name__} arrives twice"


FAULTS: List[Tuple[Callable[[Run], str], int]] = [
    (drop_dut, 3), (drop_instrument, 2), (restart_station, 1), (fail_next, 3), (time_out_next, 2),
    (slow_down, 2), (duplicate_event, 2),
]
VISIBLE_FAULTS = {drop_dut, drop_instrument, restart_station}   # each must show up in the log at once


# ---- invariants -----------------------------------------------------------------------------------

def _station_busy(h: Harness) -> bool:
    fake = h.fake
    return (any(not a.finished for a in fake.sequencer.activities.values()) or bool(fake.bench._activities)
            or bool(fake.station_tests.runs))


def _app_busy(h: Harness) -> List[str]:
    s, shell = h.services, h.shell
    flags = {"sequence": shell.sequences.running, "action run": s.actions.running,
             "test run": shell.stationTests.running, "dump": s.dumps.running, "read all": s.read_all.running,
             "custom function": shell.customFunctions.running, "chamber wait": shell.chamber.waiting,
             "eca capture": shell.eca.capturing}
    return [name for name, busy in flags.items() if busy]


def check_station_busy_is_shown(run: Run) -> None:
    """At every step: whatever the station is running, the app shows as running (so nothing can be lost)."""
    h, s, shell = run.h, run.h.services, run.h.shell
    if any(not a.finished for a in h.fake.sequencer.activities.values())             and not (shell.sequences.running or s.actions.running):
        run.fail("the station is running a sequence or actions, but neither page shows it running")
    if h.fake.station_tests.runs and not shell.stationTests.running:
        run.fail("the station is running tests, but the Tests page doesn't show it")
    kinds = {h.fake.bench.instruments[a.instrument_id].kind for a in h.fake.bench._activities.values()}
    if "chamber" in kinds and not shell.chamber.waiting:
        run.fail("the chamber is waiting for stable, but the page doesn't show it")
    if "eca" in kinds and not shell.eca.capturing:
        run.fail("the ECA is capturing, but the page doesn't show it")


def settle(run: Run) -> None:
    """Lets every activity and one-shot task finish (periodic polling keeps going)."""
    h = run.h
    h.fake.auto_resolve = True
    h.fake.release()
    for _ in range(SETTLE_LIMIT_MS // 1000):
        h.scheduler.run_pending()
        if not _station_busy(h) and not _app_busy(h):
            return
        h.scheduler.advance(1000)


def check_invariants(run: Run) -> None:
    h = run.h
    settle(run)
    if _station_busy(h):
        run.fail("the station is still busy after settling")
    busy = _app_busy(h)
    if busy:
        run.fail(f"the station is idle but the app still shows busy: {', '.join(busy)}")
    state = h.state
    expected = state.can("automation.seq.run")
    if h.shell.sequences.canRun != expected or h.shell.actions.canRun != expected:
        run.fail(f"Run buttons don't match the station: can run = {expected}, sequences = "
                 f"{h.shell.sequences.canRun}, actions = {h.shell.actions.canRun}")
    for path in (h.home / ".sibench").glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            run.fail(f"{path.name} isn't valid JSON: {exc}")


# ---- the run --------------------------------------------------------------------------------------

def _pick(rng: random.Random, table: List[Tuple[Callable[[Run], str], int]]) -> Callable[[Run], str]:
    return rng.choices([fn for fn, _ in table], weights=[w for _, w in table])[0]


def play(seed: int, steps: int, home: Path, check_every: int = 8, harness: Optional[Harness] = None,
         after_step: Callable[[], None] = lambda: None, skip: Tuple[Callable[[Run], str], ...] = ()) -> Run:
    """harness: an app already running with its window (the QML variant); after_step lets the window catch up;
    skip: steps to leave out (the QML variant can't answer Windows' own file dialogs)."""
    rng = random.Random(seed)
    steps_table = [(fn, w) for fn, w in STEPS if fn not in skip]
    h = harness or Harness(home)
    h.fake.connect_dut(2)
    h.scheduler.run_pending()
    run = Run(seed, h, rng)
    for i in range(1, steps + 1):
        is_fault = rng.random() < 0.2
        action = _pick(rng, FAULTS if is_fault else steps_table)
        before = len(h.services.log.lines)
        try:
            run.trail.append(f"{i:3d}. {action(run)}")
            if action in VISIBLE_FAULTS and run.trail[-1].startswith(f"{i:3d}. FAULT"):
                new = h.services.log.lines[before:]
                if not any(line.level in ("warning", "error") for line in new):
                    run.fail(f"{action.__name__} left no warning or error in the log")
            check_station_busy_is_shown(run)
            h.scheduler.advance(rng.choice([0, 50, 200, 600, 1500]))
            check_station_busy_is_shown(run)
            after_step()
            if i % check_every == 0:
                check_invariants(run)
        except ChaosFailure:
            raise
        except Exception as exc:  # any error escaping a step would have been a crash (or a crash-guard toast)
            run.fail(f"{type(exc).__name__}: {exc}")
    check_invariants(run)
    return run
