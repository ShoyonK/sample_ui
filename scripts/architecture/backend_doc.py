"""Writes docs/BACKEND_DESIGN.md: what the station service must implement for the SiRAT GUI.

Run from the repo root:  uv run python scripts/architecture/backend_doc.py

Generated from the code: example payloads (payloads.py, captured from the fake station), requires
(core/requires.py), callers (callgraph.py) and operation kinds (core/ops.py). The function descriptions below
are written by hand from docs/API_DESIGN.md and the fake's behaviour; keep them in step with both.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "src")]
import callgraph  # noqa: E402
import flowstyle  # noqa: E402
import payloads  # noqa: E402
from sirat_ui.core.ops import KINDS  # noqa: E402
from sirat_ui.core.requires import METHOD_REQUIRES, TAG_TEXT  # noqa: E402

# ------------------------------------------------------------------------------------------------- specs
# name: (signature, what it does, errors besides wrong_state / invalid_params, facts and events it changes)
F = {
    # ---- sys
    "sys.hello": ("sys.hello(client: str, protocol: int) -> {release_id: str, protocol: int, server_time: str}",
                  "First call on a connection. Returns the service build and the protocol version it speaks; the "
                  "GUI shows the release in the status bar.",
                  "—", "—"),
    "sys.subscribe": ("sys.subscribe(topics: list[str]) -> Empty",
                      "Starts pushing events for these topics on this connection: `status`, `activity`, `watch`, "
                      "`instrument`, `log`. The GUI subscribes to all five right after `sys.hello`.",
                      "—", "—"),
    "sys.status": ("sys.status() -> StationStatus",
                   "The facts for all four positions and every instrument. The GUI calls it at startup and whenever "
                   "an event `seq` gap means it may have missed a `status.changed`.",
                   "—", "—"),
    "sys.recover": ("sys.recover(pos: Position) -> Empty",
                    "Applies the safe state to a position and clears its `fault`. A hardware error during an "
                    "activity sets the fault, and until it's cleared the position refuses `automation.seq.run` (and "
                    "`dut.connect` / `dut.reconnect`). The GUI shows a Recover button next to the status while the "
                    "selected position has a fault.",
                    "—", "`fault` cleared, `activity` idle; `status.changed`"),
    # ---- dut
    "dut.connect": ("dut.connect(pos: Position, config_type: 'EFR32' | 'EFX', config_file: str = '', "
                    "rpc: RpcAddress | None = None) -> {chip: ChipInfo, rpc: RpcAddress}",
                    "Bench setup for the position, then the RPC connection to the DUT. `rpc` omitted means the "
                    "address in the workspace config. Sends `log.line` progress (`source: dut.connect`, `pos`) while it "
                    "runs, so the connect sheet can show the steps.",
                    "`timeout` (address unreachable), `hardware_error`",
                    "`dut_connected` true; `status.changed`"),
    "dut.reconnect": ("dut.reconnect(pos: Position) -> Empty",
                      "RPC only (`rpc_io.Connect()`), keeping the bench setup. Used by the disconnect-recovery dialog "
                      "after a firmware assert.",
                      "`not_found` (position never connected), `timeout`",
                      "`dut_connected` true; `status.changed`"),
    "dut.disconnect": ("dut.disconnect(pos: Position) -> Empty",
                       "Closes the DUT connection.",
                       "—",
                       "Reset rules (below): `phy`, `watching`, `rf_path` cleared, watches and console sessions of the "
                       "position end; `status.changed`"),
    "dut.probe": ("dut.probe(pos: Position, rpc: RpcAddress | None, timeout_s: float) -> "
                  "{ok: bool, latency_ms: float, detail: str}",
                  "Can that address be reached? Never connects or disconnects anything, so testing a setting can't "
                  "drop a live connection. An unreachable address is `ok: false`, not an error.",
                  "—", "—"),
    "dut.info": ("dut.info(pos: Position) -> DutInfo",
                 "System information (req 31): chip, revision, hardware identifiers, the RPC address and timeout, and "
                 "the firmware application if it reports one.",
                 "—", "—"),
    "dut.load_phy": ("dut.load_phy(pos: Position, phy: {kind: 'lpw', name} | {kind: 'wifi', config: WifiPhyConfig})"
                     " -> {name: str, function: str, overrides: [[key, value]]}",
                     "LPW: `reset_and_download_lpw_phy(name)`. WiFi: builds the config and calls `load_wifi_phy`; "
                     "`overrides` are the TestInputs values it set, shown in the success dialog.",
                     "`invalid_params` (WiFi on a non-Everest DUT, channel outside the standard's band), "
                     "`hardware_error`",
                     "`phy` set; `status.changed`, `log.line`"),
    "dut.set_rpc_timeout": ("dut.set_rpc_timeout(seconds: float 1..300) -> Empty",
                            "Station-wide: every DUT's RPC timeout, and the default `timeout_ms` of calls.",
                            "—", "—"),
    # ---- registers
    "registers.tree": ("registers.tree(pos: Position) -> RegisterTree",
                       "Every peripheral, register and field of the connected chip, with descriptions, enum values, "
                       "reset values and the six access types. The GUI caches it by (chip, revision, `tree_id`).",
                       "—", "—"),
    "registers.read": ("registers.read(pos: Position, name: str) -> {value: int}",
                       "One register by `PERIPHERAL.REGISTER`. A single read of a read-sensitive register is allowed "
                       "(the user asked for exactly that register).",
                       "`not_found`, `access_denied` (write-only), `dut_disconnected`",
                       "—"),
    "registers.read_many": ("registers.read_many(pos: Position, names: list[str], include_read_sensitive: bool = "
                            "false) -> {items: [{name, value | error}]}",
                            "Bulk read for dumps, Read All, the logger and Radio Calculator diff. One bad register "
                            "doesn't fail the call: its item carries the error instead.",
                            "Per item: `read_sensitive`, `not_found`, `access_denied`",
                            "—"),
    "registers.write": ("registers.write(pos: Position, name: str, value: int, confirm: bool = false, verify: bool = "
                        "true) -> WriteRes",
                        "Writes and (with `verify`) reads back. A read-back that differs is `verified: false`, not an "
                        "error: the write happened and the GUI warns.",
                        "`confirmation_required` (critical peripheral without `confirm`), `access_denied`, "
                        "`out_of_range`, `not_found`",
                        "—"),
    "registers.write_field": ("registers.write_field(pos: Position, name: str, field: str, value: int, confirm: bool "
                              "= false, verify: bool = true) -> WriteRes",
                              "Read-modify-write of one field under the position lock.",
                              "As `registers.write`", "—"),
    "registers.watch": ("registers.watch(pos: Position, names: list[str], interval_s: float 0.1..60, "
                        "include_read_sensitive: bool = false) -> {sub_id: str}",
                        "Starts a subscription that pushes `registers.watch` events every interval. If the client is "
                        "slow, keep only the newest values per subscription (dropped ones don't use a `seq`).",
                        "`read_sensitive`, `not_found`",
                        "`watching` true; `registers.watch` events"),
    "registers.unwatch": ("registers.unwatch(sub_id: str) -> Empty",
                          "Ends a subscription. Unknown ids are not an error (the DUT may have dropped it already).",
                          "—", "`watching` false when the position has no other watch"),
    # ---- memory
    "memory.read": ("memory.read(pos: Position, address: int, size: int 1..4096) -> {address: int, data: base64}",
                    "Aligns the start down and the end up to 4 bytes and returns the aligned `address` it actually "
                    "read. The GUI formats bytes, words or dwords, little-endian.",
                    "`out_of_range` (unmapped address)", "—"),
    "memory.write": ("memory.write(pos: Position, address: int, value: int, size: 1 | 2 | 4) -> "
                     "{address, value_written, value_readback}",
                     "Read-modify-write of the aligned 4-byte word under the position lock. The GUI confirms every "
                     "memory write before calling.",
                     "`access_denied` (flash), `out_of_range`, `invalid_params` (crosses a 4-byte word)",
                     "`log.line`"),
    # ---- rf
    "rf.paths": ("rf.paths() -> {names: list[str]}",
                 "The RF switch's path names, from the switch configuration.", "—", "—"),
    "rf.connect": ("rf.connect(pos: Position, path: str) -> Empty",
                   "Connects a switch path to a DUT position.",
                   "`not_found` (unknown path), `instrument_error`",
                   "`rf_path` set; `status.changed`, `log.line`"),
    "rf.disconnect": ("rf.disconnect(pos: Position) -> Empty",
                      "Disconnects the position's path.", "`instrument_error`",
                      "`rf_path` cleared; `status.changed`, `log.line`"),
    "rf.prs_signals": ("rf.prs_signals(pos: Position) -> {family: str, module: str, signals: list[str]}",
                       "The PRS signals the chip family's `pti_prs_module` offers. The GUI falls back to a built-in "
                       "list if this fails.", "—", "—"),
    "rf.prs_route": ("rf.prs_route(pos: Position, route: {signal, pin: PA0..PD7, channel: 0..11}) -> Empty",
                     "Routes an internal signal to a GPIO pin; `signal: DISABLE` removes a route.",
                     "`invalid_params` (port A/B with channels 6–11, port C/D with 0–5)", "`log.line`"),
    # ---- instruments
    "instruments.list": ("instruments.list() -> {instruments: list[InstrumentFacts]}",
                         "The station's instruments. The GUI currently reads them from `sys.status` instead.",
                         "—", "—"),
    "instruments.connect": ("instruments.connect(id: str, address: str | None = None) -> Empty",
                            "Connects an instrument that dropped (the Connect button on each instrument card).",
                            "`not_found`, `instrument_error`", "`connected` true; `status.changed`"),
    "instruments.siggen.get": ("instruments.siggen.get(id: str) -> SiggenConfig",
                               "What the signal generator is loaded with now (Load from instrument).",
                               "`instrument_error`", "—"),
    "instruments.siggen.set": ("instruments.siggen.set(id: str, config: SiggenConfig) -> Empty",
                               "Applies type, waveform, frequency (Hz on the wire), power and overrides.",
                               "`invalid_params` (power outside −150..30 dBm, unknown waveform), `instrument_error`",
                               "`log.line`"),
    "instruments.siggen.waveforms": ("instruments.siggen.waveforms(id: str, reload: bool = false) -> "
                                     "{names: list[str]}",
                                     "The waveform files the instrument has; `reload` rescans them.",
                                     "`instrument_error`", "—"),
    "instruments.siggen.trigger": ("instruments.siggen.trigger(id: str, mode: 'infinite' | 'single') -> Empty",
                                   "Starts the waveform.", "`instrument_error`", "`log.line`"),
    "instruments.siggen.rf": ("instruments.siggen.rf(id: str, on: bool) -> Empty",
                              "Switches the RF output.", "`instrument_error`", "`log.line`"),
    "instruments.chamber.read": ("instruments.chamber.read(id: str) -> {actual_c, target_c, stable}",
                                 "The live reading; the GUI polls it at the interval the user picks while the page "
                                 "is visible.", "`instrument_error`", "—"),
    "instruments.chamber.set_temp": ("instruments.chamber.set_temp(id: str, celsius: float) -> Empty",
                                     "Returns when the setpoint is accepted, not when it's reached.",
                                     "`instrument_error`", "`log.line`"),
    "instruments.chamber.wait_stable": ("instruments.chamber.wait_stable(id: str, tolerance_c: float = 0.5, hold_s: "
                                        "float = 60, timeout_s: float = 3600) -> ActivityRef",
                                        "An activity: done after the reading has stayed within tolerance for "
                                        "`hold_s`. Progress about once a second; abortable.",
                                        "In `activity.finished.error`: `timeout`, `aborted`, `instrument_error`",
                                        "Instrument `activity`; `activity.progress`, `activity.finished`"),
    "instruments.eca.sources": ("instruments.eca.sources(id: str) -> {channels: list[str], triggers: list[str]}",
                                "What can be captured and what can trigger. `immediate` is always allowed as a "
                                "trigger.", "`instrument_error`", "—"),
    "instruments.eca.capture": ("instruments.eca.capture(id: str, spec: CaptureSpec) -> ActivityRef",
                                "An activity (arm, wait for trigger, capture, upload). `activity.finished.result` is "
                                "`{capture_id}`. Keep the capture until its last page is read, or for 1 hour.",
                                "`invalid_params` (unknown channel, more than 1,000,000 samples per channel)",
                                "Instrument `activity`; `activity.progress`, `activity.finished`"),
    "instruments.eca.result": ("instruments.eca.result(capture_id: str, offset: int = 0, count: int = 65536) -> "
                               "CapturePage",
                               "One page of samples per channel: base64, little-endian int16, in mV. `more: false` "
                               "on the last page.", "`not_found` (unknown or expired capture)", "—"),
    # ---- automation and activity
    "automation.seq.run": ("automation.seq.run(pos: Position, ops: list[Op], stop_on_error: bool = true) -> "
                           "ActivityRef",
                           "Runs the ops in order as one activity; ops in one run share one Python namespace. Each "
                           "progress event echoes the op's `group` (the action it came from). The ops are listed in "
                           "the appendix.",
                           "In `activity.finished.error`: the failing op's error; `aborted`",
                           "Position `activity`; `activity.progress` per op, `activity.finished` once"),
    "activity.abort": ("activity.abort(activity_id: str) -> Empty",
                       "Cooperative: takes effect at the next wrapped hardware call and ends in the safe state. The "
                       "activity still sends exactly one `activity.finished` (with `aborted`).",
                       "None: an unknown or finished id is ignored (the GUI may abort twice)", "—"),
    # ---- advanced
    "advanced.console.open": ("advanced.console.open(pos: Position) -> {session_id: str}",
                              "A Python namespace holding `dut` and the test utilities, kept until it's closed, the "
                              "client disconnects, or the DUT disconnects.", "—", "—"),
    "advanced.console.exec": ("advanced.console.exec(session_id: str, code: str, mode: 'auto' | 'eval' | 'exec' = "
                              "'auto') -> ExecResult",
                              "`auto` tries `eval` and falls back to `exec` on `SyntaxError`. Captures stdout and "
                              "stderr; an exception is a successful reply with `error` set, not an error reply.",
                              "`not_found` with `data.session_id` (session ended; the GUI reopens once and retries)",
                              "—"),
    "advanced.console.names": ("advanced.console.names(session_id: str) -> {names: list[{name, type, doc}]}",
                               "The namespace's public names, for the console's Help.", "`not_found`", "—"),
    "advanced.console.close": ("advanced.console.close(session_id: str) -> Empty",
                               "Drops the namespace. Unknown ids are not an error.", "—", "—"),
    "advanced.custom_function": ("advanced.custom_function(pos: Position, name: str, code: str, session_id: str | "
                                 "None = None) -> ExecResult",
                                 "Runs the code wrapped in a function, so a top-level `return` works. With a "
                                 "`session_id` it uses that namespace and stores `result_<name>` and "
                                 "`last_dut_api_result` there; without one it gets a fresh namespace.",
                                 "`not_found` (session)", "`log.line`"),
    "advanced.dut_control.describe": ("advanced.dut_control.describe(pos: Position) -> ApiTree",
                                      "The `dut.dut_control` API as packages, modules and methods with signatures, "
                                      "docstrings and parameters. Classes win over modules, private methods are "
                                      "skipped, and the injected `dut` parameter is left out.", "—", "—"),
    "advanced.dut_control.invoke": ("advanced.dut_control.invoke(pos: Position, path: str, args: list, kwargs: "
                                    "dict) -> {result_text, result_json, result_type}",
                                    "Calls the method, injecting `dut` when it takes it. `result_text` is formatted "
                                    "for reading; `result_json` is the value when it's JSON.",
                                    "`not_found` (path), `invalid_params` (arguments don't bind), `hardware_error` "
                                    "with `data.cause: rpc_timeout | rpc_transport | rail_assert | other` and "
                                    "`data.traceback`",
                                    "`log.line`"),
}
NOT_IN_FRONTEND = {
    "sys.describe": "Method schemas for tooling. Not needed by the GUI.",
    "activity.status": "Polling an activity. The GUI relies on `activity.*` events.",
    "instruments.disconnect": "No screen disconnects an instrument.",
}
AREAS = [("sys", "Handshake and station status"), ("dut", "DUT connection"), ("registers", "Registers"),
         ("memory", "Memory"), ("rf", "RF switch and PRS"), ("instruments", "Instruments"),
         ("automation", "Running actions"), ("activity", "Activities"), ("advanced", "Python and DUT control")]
SLICES = [
    ("1. Connect and registers", "Registers page, connection sheet, system info, history, Read All, favorites",
     ["sys.hello", "sys.subscribe", "sys.status", "dut.connect", "dut.disconnect", "dut.reconnect", "dut.info",
      "dut.probe", "dut.set_rpc_timeout", "registers.tree", "registers.read", "registers.read_many",
      "registers.write", "registers.write_field"]),
    ("2. Live values", "Watch list, data logger; dumps and Radio Calculator diff already work from slice 1",
     ["registers.watch", "registers.unwatch"]),
    ("3. Actions and sequences", "Actions page, Sequences page, every Add to Actions, Recover after a fault",
     ["automation.seq.run", "activity.abort", "sys.recover"]),
    ("4. Radio", "Radio and PHY page", ["dut.load_phy", "rf.prs_signals", "rf.prs_route"]),
    ("5. Advanced", "Console, custom functions, DUT control explorer, memory viewer",
     ["advanced.console.open", "advanced.console.exec", "advanced.console.names", "advanced.console.close",
      "advanced.custom_function", "advanced.dut_control.describe", "advanced.dut_control.invoke", "memory.read",
      "memory.write"]),
    ("6. Instruments", "Instruments page",
     ["instruments.connect", "rf.paths", "rf.connect", "rf.disconnect", "instruments.siggen.get",
      "instruments.siggen.set", "instruments.siggen.waveforms", "instruments.siggen.trigger",
      "instruments.siggen.rf", "instruments.chamber.read", "instruments.chamber.set_temp",
      "instruments.chamber.wait_stable", "instruments.eca.sources", "instruments.eca.capture",
      "instruments.eca.result"]),
]


# ------------------------------------------------------------------------------------------------- helpers
def trim(value, depth=0):
    """Long lists and strings shortened for reading; the shape stays."""
    if isinstance(value, list):
        if len(value) > 3:
            return [trim(v, depth + 1) for v in value[:2]] + [f"… {len(value) - 2} more"]
        return [trim(v, depth + 1) for v in value]
    if isinstance(value, dict):
        items = list(value.items())
        out = {k: trim(v, depth + 1) for k, v in items[:12]}
        if len(items) > 12:
            out["…"] = f"{len(items) - 12} more keys"
        return out
    if isinstance(value, str) and len(value) > 100:
        return value[:97] + "…"
    return value


def js(value) -> str:
    return json.dumps(trim(value), indent=2, ensure_ascii=False)


def frame_request(name, params, rid=7):
    return {"id": rid, "method": name.split(" ")[0], "params": params}


# Results the fake returns unwrapped, and the field the wire object uses (contract gaps, item 1)
WRAP = {"registers.read": "value", "registers.read_many": "items", "registers.watch": "sub_id",
        "rf.paths": "names", "instruments.siggen.waveforms": "names", "instruments.list": "instruments",
        "instruments.chamber.wait_stable": "activity_id", "instruments.eca.capture": "activity_id",
        "automation.seq.run": "activity_id", "advanced.console.open": "session_id",
        "advanced.console.names": "names"}


def wire_event(method: str, event):
    """call.late carries the late call's result, which gets the same wire shape as a reply."""
    if event.get("event") == "call.late" and "result" in event.get("data", {}):
        return {**event, "data": {**event["data"], "result": wire_result(method, event["data"]["result"])}}
    return event


def wire_result(method: str, result):
    if result is None:
        return {}                                   # Empty
    if method in WRAP:
        return {WRAP[method]: result}
    return result


def example(name, cap) -> str:
    if name not in cap:
        return ""
    e = cap[name]
    parts = [f"Request\n\n```json\n{js(frame_request(name, e.get('params', {})))}\n```\n"]
    if "error" in e:
        parts.append(f"Reply (error)\n\n```json\n{js({'id': 7, 'ok': False, 'error': e['error']})}\n```\n")
    else:
        result = wire_result(name.split(" ")[0], e.get("result"))
        parts.append(f"Reply\n\n```json\n{js({'id': 7, 'ok': True, 'result': result})}\n```\n")
    if e.get("events"):
        evs = [wire_event(name.split(" ")[0], ev) for ev in e["events"][:4]]
        more = f"\n… and {len(e['events']) - 4} more events of the same kinds" if len(e["events"]) > 4 else ""
        parts.append("Events it causes\n\n```json\n" + "\n".join(js(ev) for ev in evs) + f"\n```{more}\n")
    return "\n".join(parts)


def callers(name, vm_eps) -> str:
    vms = sorted(v for v, eps in vm_eps.items() if name in eps)
    bg = callgraph.SERVICE_CALLS.get(name)
    who = vms + ([f"{bg[0]} ({bg[1]})"] if bg else [])
    return ", ".join(who) if who else "nothing yet (see contract gaps)"


def requires(name) -> str:
    tags = METHOD_REQUIRES.get(name, ())
    return ", ".join(f"`{t}`" for t in tags) or "—"


# ------------------------------------------------------------------------------------------------- document
def build() -> str:
    cap = payloads.capture()
    vm_eps, api, _ = callgraph.compute()
    s = []
    s.append(f"""# SiRAT station service: backend design

What the station service has to implement so the SiRAT GUI works against real hardware: the functions, the exact
payloads that go in and come out, the events it pushes, the state it keeps, and the order to build it in.

- **The contract** is [API_DESIGN.md](API_DESIGN.md) (revision 2). This document doesn't change it; it makes it
  concrete for whoever builds the service. Where the two disagree, API_DESIGN.md wins and the difference is listed
  in [contract gaps](#10-contract-gaps-to-settle).
- **The reference implementation** is the frontend's fake station (`src/sirat_ui/gateway/fake/`). It enforces the
  same requires, returns the same error codes and is what the GUI is tested against. Every example payload below
  was captured by calling it, then put in the API's wire format.
- **Who calls what** is in [ARCHITECTURE.md, section 18](ARCHITECTURE.md#18-viewmodels-to-backend-endpoints).

Generated by `scripts/architecture/backend_doc.py`; rerun it after changing the API or the fake.

Contents

1. [The service at a glance](#1-the-service-at-a-glance)
2. [Suggested structure](#2-suggested-structure)
3. [Messages on the wire](#3-messages-on-the-wire)
4. [A client session](#4-a-client-session)
5. [State the service keeps](#5-state-the-service-keeps)
6. [Functions to implement](#6-functions-to-implement)
7. [Events to push](#7-events-to-push)
8. [Activities](#8-activities)
9. [Errors](#9-errors)
10. [Contract gaps to settle](#10-contract-gaps-to-settle)
11. [Build order](#11-build-order)
12. [Appendix: operations in automation.seq.run](#12-appendix-operations-in-automationseqrun)
""")

    n_funcs = len(F)
    s.append(f"""## 1. The service at a glance

One process per station, reached over TCP on loopback. {n_funcs} functions in {len(AREAS)} areas, 7 kinds of event,
facts for 4 DUT positions and the instruments. Every call goes through the same pipeline.

```mermaid
flowchart TB
    gui["SiRAT GUI<br/>client SDK"]
    subgraph service["Station service"]
        direction TB
        framing["Framing<br/>4-byte length + UTF-8 JSON, 16 MB max"]
        dispatch["Dispatcher<br/>method name → handler, request id"]
        validate["Validation<br/>pydantic models, unknown fields rejected"]
        requires["Requires check<br/>facts + METHOD_REQUIRES → wrong_state"]
        lock["Position / instrument lock<br/>busy if held; timeout → still_running"]
        handlers["Domain handlers<br/>sys · dut · registers · memory · rf ·<br/>instruments · automation · activity · advanced"]
        adapters["Hardware adapters<br/>DUT library (rm, rpc_io, dut_control) · instrument drivers"]
        facts[("Facts<br/>positions, instruments")]
        runner["Activity runner<br/>progress, abort, finished once"]
        bus["Event bus<br/>per-connection seq, watch coalescing"]
        framing --> dispatch --> validate --> requires --> lock --> handlers --> adapters
        requires -.->|"reads"| facts
        handlers -.->|"updates"| facts
        handlers --> runner
        facts -.->|"status.changed"| bus
        runner -.->|"activity.*"| bus
    end
    gui <-->|"requests / replies"| framing
    bus -->|"events"| gui
```
""")

    s.append("""## 2. Suggested structure

A layout that keeps the contract, the rules and the hardware apart. Names are suggestions.

| Part | What it holds | Notes |
|---|---|---|
| `contracts/` | The pydantic models: every request, result and event in this document | Shared with the client SDK; no hardware imports (CI check) |
| `server/` | Framing, connections, dispatcher, subscriptions, `seq` | One task per connection; replies may go out of order |
| `facts.py` | `PositionFacts`, `InstrumentFacts`, reset rules | Every change emits `status.changed` |
| `requires.py` | `METHOD_REQUIRES` and `check_requires` | Copy `src/sirat_ui/core/requires.py`: the GUI uses the same table to enable buttons |
| `locks.py` | One lock per position and per instrument | A timed-out call keeps its lock until it really ends |
| `activities.py` | Activity runner: `starting → executing → done`, abort flag, `finished` exactly once | Hardware errors during an activity set the position's `fault` |
| `domains/<area>.py` | One handler module per area in section 6 | Map library exceptions to error codes here |
| `adapters/` | The DUT library and instrument drivers behind small interfaces | Lets the service run against simulators in CI |
""")

    # ---- wire
    err_example = cap["registers.read (no DUT)"]["error"]
    late = cap["registers.write (timeout)"]
    late_event = dict(late["events"][-1])
    late_event["data"] = {**late_event["data"], "result": wire_result("registers.write", late_event["data"].get("result"))}
    s.append(f"""## 3. Messages on the wire

Each frame is a 4-byte big-endian length, then a UTF-8 JSON body (16 MB at most). Requests, replies and events
share the connection.

Request

```json
{js({"id": 17, "method": "registers.read", "params": {"pos": 1, "name": "BUFC.LPMODE"}, "timeout_ms": 5000})}
```

Reply, success. The result is always an object (see [contract gaps](#10-contract-gaps-to-settle), item 1)

```json
{js({"id": 17, "ok": True, "result": {"value": 1}})}
```

Reply, failure

```json
{js({"id": 17, "ok": False, "error": err_example})}
```

Event

```json
{js({"event": "status.changed", "seq": 912, "data": cap["sys.status"]["result"]})}
```

**Rules**

- `id` matches replies to requests; replies may come in any order.
- `seq` goes up by one for every event *sent* on the connection. A gap means events were lost, so the GUI
  refetches `sys.status`. Watch events the service drops (keeping only the newest per subscription) don't use a
  `seq`.
- `timeout_ms` defaults to the RPC timeout (`dut.set_rpc_timeout`, 5 s, range 1–300 s).
- A call that runs past `timeout_ms` is answered with `timeout` and `data.still_running: true`. The hardware call
  keeps going and keeps its lock (other calls get `busy` with `data.request_id`). When it ends, the service sends
  `call.late`, so the GUI learns whether a timed-out write happened:

```json
{js({"id": 31, "ok": False, "error": late["error"]})}
{js({**late_event, "seq": 913})}
```
""")

    s.append("""## 4. A client session

```mermaid
sequenceDiagram
    participant GUI
    participant Svc as Station service
    participant HW as DUT / instruments
    GUI->>Svc: sys.hello(client, protocol)
    Svc-->>GUI: release_id, protocol, server_time
    GUI->>Svc: sys.subscribe([status, activity, watch, instrument, log])
    GUI->>Svc: sys.status()
    Svc-->>GUI: StationStatus
    GUI->>Svc: dut.connect(pos=1, config_type)
    Svc-->>GUI: log.line (bench setup), log.line (RPC connect)
    Svc->>HW: bench setup, rpc_io.Connect()
    Svc-->>GUI: status.changed (dut_connected=true)
    Svc-->>GUI: chip, rpc
    GUI->>Svc: registers.tree(pos=1)
    Svc-->>GUI: RegisterTree
    GUI->>Svc: registers.read / write … (user actions)
    GUI->>Svc: registers.watch(pos=1, names, 1.0)
    loop every interval
        Svc-->>GUI: registers.watch {sub_id, values}
    end
    HW--xSvc: link lost
    Svc-->>GUI: dut.disconnected (after the 2 s debounce)
    Svc-->>GUI: status.changed (dut_connected=false, watches ended)
```
""")

    # ---- state
    req_rows = "\n".join(f"| `{m}` | {requires(m)} |" for m in sorted(METHOD_REQUIRES))
    tag_rows = "\n".join(f"| `{t}` | {txt} |" for t, txt in TAG_TEXT.items())
    s.append(f"""## 5. State the service keeps

**Facts** are the only state the requires check reads. Any change sends `status.changed` with the whole
`StationStatus`:

```json
{js(cap["sys.status"]["result"])}
```

**Tags** a method can require (`wrong_state.data.missing` lists tags, never fact names):

| Tag | Met when (the GUI's wording) |
|---|---|
{tag_rows}

`idle` means the position's `activity` is idle, or, for `instruments.*` calls with an `id`, that instrument's.

**Reset rules**

- A DUT disconnect clears `phy`, `watching` and `rf_path`, ends that position's watches and closes its console
  sessions.
- Loading a PHY changes nothing else.
- An instrument drop ends that instrument's activity with `instrument_error`.
- `hardware_error` and `dut_disconnected` update the facts *before* the reply, so the next `sys.status` is right.

**Requires per method** (the same table the GUI uses, `src/sirat_ui/core/requires.py`):

| Method | Requires |
|---|---|
{req_rows}
""")

    # ---- functions
    s.append("## 6. Functions to implement\n\nEach area starts with a summary; each function then has its "
             "signature, what it must do, its errors besides `wrong_state` and `invalid_params`, what it changes, who "
             "calls it, and a captured request and reply.\n")
    for prefix, title in AREAS:
        names = [n for n in F if n.split(".")[0] == prefix]
        rows = "\n".join(f"| `{n}` | {requires(n)} | {callers(n, vm_eps)} |" for n in names)
        s.append(f"### {prefix}: {title}\n\n| Function | Requires | Called by |\n|---|---|---|\n{rows}\n")
        for n in names:
            sig, does, errors, changes = F[n]
            body = (f"#### `{n}`\n\n```python\n{sig}\n```\n\n{does}\n\n"
                    f"- **Errors:** {errors}\n- **Changes:** {changes}\n- **Called by:** {callers(n, vm_eps)}\n\n")
            ex = example(n, cap)
            extra = [k for k in cap if k.startswith(n + " (")]
            for k in extra:
                ex += f"\n*{k.split('(', 1)[1].rstrip(')')}:*\n\n" + example(k, cap)
            if n == "registers.tree":
                ex = REGISTER_TREE_EXAMPLE
            if ex:
                body += f"<details><summary>Example payloads</summary>\n\n{ex}\n</details>\n"
            s.append(body)
    if NOT_IN_FRONTEND:
        rows = "\n".join(f"| `{n}` | {why} |" for n, why in NOT_IN_FRONTEND.items())
        s.append(f"### In the API design but not used by the GUI\n\n| Function | Why it can wait |\n|---|---|\n{rows}\n")

    # ---- events
    seen = {}
    for key, e in cap.items():
        for ev in e.get("events", []):
            seen.setdefault(ev["event"], wire_event(key.split(" ")[0], ev))
    rows = """| Event | Data | When | GUI listener |
|---|---|---|---|
| `status.changed` | `StationStatus` | Any fact changes | ConnectionService → `StationState.apply_status` |
| `activity.progress` | `activity_id, pos? \\| instrument_id?, step, total, message, group?` | Each step | ActivityTracker → the service that started it |
| `activity.finished` | `activity_id, pos? \\| instrument_id?, ok, results[], result?, error?` | Exactly once per activity | ActivityTracker |
| `registers.watch` | `sub_id, pos, ts, values[{name, value}]` | Every interval; only the newest kept if the client is slow | WatchService, DataLoggerService |
| `dut.disconnected` | `pos, cause, detected_by` | After a 2 s debounce | ConnectionService → recovery dialog |
| `instrument.changed` | `InstrumentFacts` | An instrument connects, drops or changes activity | (instruments also arrive in `status.changed`) |
| `call.late` | `request_id, ok, result \\| error` | A timed-out call finished | LogService |
| `log.line` | `ts, level, source, text, pos?` | Progress and notable actions | LogService (Log panel) |"""
    examples = "\n".join(js({**ev, "seq": 100 + i}) for i, ev in enumerate(seen.values()))
    s.append(f"""## 7. Events to push

Only after `sys.subscribe`, and only for the subscribed topics.

{rows}

Captured examples (one of each kind the GUI receives):

```json
{examples}
```
""")

    # ---- activities
    run = cap["automation.seq.run"]
    abort = cap["activity.abort"]
    s.append(f"""## 8. Activities

Long work returns an `activity_id` at once and reports through events. An activity belongs to one position
(`pos`) or one instrument (`instrument_id`), and each has at most one at a time.

```mermaid
stateDiagram-v2
    [*] --> starting
    starting --> executing
    executing --> done
    starting --> aborting: activity.abort
    executing --> aborting: activity.abort
    aborting --> done
    done --> [*]
```

- `activity.finished` is sent **exactly once**, including after an abort or a service restart.
- Abort is cooperative: it takes effect at the next wrapped hardware call and ends in the safe state.
- A hardware error during an activity on a position sets that position's `fault`; `sys.recover` clears it.
- `automation.seq.run` sends one `activity.progress` per op, echoing the op's `group`, then `activity.finished`
  with one result per op.

A run, as the GUI sees it:

```json
{chr(10).join(js(ev) for ev in run["events"])}
```

An aborted run:

```json
{chr(10).join(js(ev) for ev in abort["events"])}
```
""")

    # ---- errors
    crit = cap["registers.write (critical, no confirm)"]["error"]
    hw = cap["advanced.dut_control.invoke (error)"]["error"]
    s.append(f"""## 9. Errors

One set of codes for every function; details go in `data`. Map library exceptions to these at the domain-handler
boundary.

| Code | Raise when | `data` |
|---|---|---|
| `wrong_state` | A required tag isn't met | `missing: [tags]` |
| `invalid_params` | Schema or range validation fails | the field |
| `unknown_method` | The method doesn't exist | — |
| `timeout` | The call ran past `timeout_ms` | `still_running: true, request_id` |
| `busy` | The position or instrument is locked by a timed-out call | `request_id` |
| `claimed` | Another owner holds the station | — |
| `confirmation_required` | A critical register written without `confirm` | `register` |
| `read_sensitive` | A read-sensitive register in `read_many` / `watch` without the opt-in | `register` |
| `access_denied` | The register, field or memory isn't readable / writable | — |
| `out_of_range` | A value doesn't fit; an address isn't mapped | `max` |
| `not_found` | Unknown register, path, id, session or capture | `session_id` for ended console sessions |
| `dut_disconnected` | The link dropped during the call | — |
| `instrument_error` | The instrument reported an error | — |
| `hardware_error` | The DUT library raised | `cause: rpc_timeout \\| rpc_transport \\| rail_assert \\| other`, `traceback` |
| `aborted` | An activity was aborted | — |
| `internal` | A bug | trace id |

The GUI words its messages from the code and `data`, never by matching message text, so keep codes and `data`
keys stable; messages can change freely.

```json
{js(crit)}
{js(hw)}
```
""")

    # ---- gaps
    unused = ", ".join(f"`{n}`" for n in NOT_IN_FRONTEND) + ", `instruments.list`"
    s.append(f"""## 10. Contract gaps to settle

Differences between API_DESIGN.md and what the frontend does today. Each needs a decision before the client SDK
adapter (`ApiStationGateway`) is written. Two found earlier are fixed in the frontend: the write result now uses
`value_written` / `value_readback` (null for write-only registers), and an unknown RF switch path is `not_found`.

| # | Gap | API design says | Frontend does | Suggestion |
|---|---|---|---|---|
| 1 | Results that are one value | `ActivityRef {{activity_id}}`, `{{sub_id}}`, `{{session_id}}`, `{{value}}`, `Empty {{}}` | Unwrapped values: `"a2"`, `"w1"`, `1`, `null` | Keep objects on the wire; the adapter unwraps them |
| 2 | `registers.tree` shape | `RegisterTree {{tree_id, peripherals[]}}`; `critical` and `read_sensitive` per peripheral | The client's own register models; the flags per register | The adapter maps `RegisterTree` to the client models |
| 3 | `sys.hello` | `hello(client, protocol)` → `release_id, protocol, server_time` | `hello()` → `release_id, protocol` | The adapter sends `client` and `protocol`; `server_time` is unused for now |
| 4 | Event field names | `pos`, `values: [{{name, value}}]` | Client models use `position`, `values: {{name: value}}` | The adapter maps; the wire follows the API (as in this document) |
| 5 | Functions nobody calls | — | {unused} have no caller in the GUI | Mark them "not v1" unless another client needs them |
| 6 | Read-sensitive registers | Placeholder rule (API_DESIGN.md §12) | Dumps and Read All skip them; single reads allowed | Settle §12 before slice 1 ships |
| 7 | Fault shape | `fault: Fault {{cause, detail, at}}` | `fault: str` (shown on the Recover button) | The adapter maps it to text, e.g. `"<cause>: <detail>"` |

Open questions carried over from API_DESIGN.md §10 (debug-mode attach, auth on a shared station, one service or
several per station, typed DUT-control arguments) also affect the service.
""")

    # ---- build order
    slice_rows = "\n".join(f"| {name} | {screens} | {', '.join(f'`{e}`' for e in eps)} |"
                           for name, screens, eps in SLICES)
    covered = {e for _, _, eps in SLICES for e in eps}
    assert covered == set(F) - {"instruments.list"}, sorted(set(F) - covered)
    chain = " --> ".join(f's{i}["{name}<br/>{len(eps)} functions"]' for i, (name, _, eps) in enumerate(SLICES))
    s.append(f"""## 11. Build order

Slices that each make whole screens work, in an order where every slice builds on the ones before. The GUI can be
pointed at the real service after slice 1 and keep using the fake for the rest.

```mermaid
flowchart TB
    {chain}
```

| Slice | Screens that start working | Functions |
|---|---|---|
{slice_rows}

The framing, dispatcher, facts, requires check, locks and event bus come first, as part of slice 1. The activity
runner comes with slice 3 and is reused by the chamber wait and the ECA capture in slice 6.
""")

    # ---- ops appendix
    rows = []
    for name, kind in KINDS.items():
        if name == "register_read":
            continue
        if kind.to_wire is not None:
            fields = {"signal_generator": "instrument_id, config: SiggenConfig",
                      "custom_function": "function_name, code"}.get(name, "built by the client")
        elif kind.wire_fields is None:
            fields = "never sent: the client expands it into its actions' ops"
        else:
            fields = ", ".join(kind.wire_fields)
        rows.append(f"| `{name}` | {fields} |")
    ops_example = cap["automation.seq.run"]["params"]
    s.append(f"""## 12. Appendix: operations in automation.seq.run

Every op is `{{"type": …}}` plus the fields below, and may carry `group` (the action it came from; progress events
echo it). The client sends only these fields, copies custom-function code in from the user's file, and expands
sequences, so the service never sees a `sequence` op. Defined in `src/sirat_ui/core/ops.py` and validated on the
GUI side by `src/sirat_ui/stores/schemas/operations.py`.

| `type` | Fields |
|---|---|
{chr(10).join(rows)}

```json
{js(frame_request("automation.seq.run", ops_example))}
```

Ops in one run share one Python namespace, so a custom function can use a variable an earlier one set.
`rf_switch` uses the run's `pos`. Run the ops in order; with `stop_on_error` the first failure ends the run.
""")
    return flowstyle.restyle("\n".join(s))


REGISTER_TREE_EXAMPLE = """The fake returns the client's own models (see [contract gaps](#10-contract-gaps-to-settle), item 2), so
this example follows the API's `RegisterTree`:

Request

```json
{"id": 7, "method": "registers.tree", "params": {"pos": 1}}
```

Reply

```json
{
  "id": 7,
  "ok": true,
  "result": {
    "tree_id": "sha256:9f2c…",
    "peripherals": [
      {
        "name": "BUFC",
        "base_address": 3120562176,
        "description": "Buffer controller",
        "critical": false,
        "read_sensitive": false,
        "registers": [
          {
            "name": "LPMODE",
            "address": 3120562184,
            "width": 32,
            "access": "rw",
            "reset_value": 1,
            "description": "Low power mode",
            "fields": [
              {"name": "LPENBYM33", "lsb": 1, "width": 1, "access": "rw",
               "description": "Low power mode enable from M33",
               "enums": [{"name": "DISABLED", "value": 0, "description": ""},
                         {"name": "ENABLED", "value": 1, "description": ""}]}
            ]
          }
        ]
      }
    ]
  }
}
```
"""


if __name__ == "__main__":
    out = HERE.parents[1] / "docs" / "BACKEND_DESIGN.md"
    out.write_text(build(), encoding="utf-8")
    print("wrote", out.relative_to(HERE.parents[1]), len(out.read_text(encoding="utf-8").splitlines()), "lines")
