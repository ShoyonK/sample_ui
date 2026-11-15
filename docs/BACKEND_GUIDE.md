# Building the station service: guide for the backend

You're building the **station service**: the process on a test station PC that owns the DUT library and the bench
instruments and answers every tool that connects to it over the Station API. The SiBench GUI is one such tool; the
debug harness is another. The GUI already exists, was built in isolation against a fake station, and is done. Your
job is the real service behind the same contract.

Read this file first, then [STATION_API.md](STATION_API.md) end to end.

## 1. What you have

| Source | What to take from it | What not to take from it |
|---|---|---|
| [STATION_API.md](STATION_API.md) | **The rules**: protocol, state, locking, timeouts, activities, what every method does | — |
| `src/station_protocol/` (this repo, moving to yours) | **The contract as code**: framing, the JSON-RPC envelope, error codes, validation, and one module per method group with every method's parameters (with ranges), result, `wrap`, `requires`, types and events. **Import it; don't rewrite it** | — |
| [STATION_API_REFERENCE.md](STATION_API_REFERENCE.md), [station_api.schema.json](station_api.schema.json) | The same shapes, generated from `station_protocol`, with real example JSON | — |
| `src/station_client/` (this repo, moving to yours) | The client every tool uses: connection, reconnect, heartbeat. Your service's other half; use it in your own tests | — |
| `tests/contract/` (this repo, moving to yours) | **Your conformance suite** (section 5). It uses only `station_protocol` and `station_client` | — |
| `src/sibench_ui/gateway/fake/` (this repo) | **Reference behaviour**: a working, tested implementation of the contract in memory. What each call returns, which error when, which events in which order, the reset rules | Its internals (it's a simulator: no real concurrency, no locks, no debounce) |
| **The legacy GUI** (the old, vibe-coded SiRAT) | **Evidence of how the hardware is driven**: which library objects and functions are called, with which arguments and units, in which order, what they raise, what they return | Its architecture, its API shapes, its threading, its globals, its error handling. It is not a spec |
| *Migrating the Debug Harness to the Station Service Design* | The station repository's layout, and how the debug harness moves onto the same service | Its lease and token parts: out of scope for now |
| [API_DESIGN.md](API_DESIGN.md) | Why the contract is shaped as it is (revision 2 and its decisions) | Anything STATION_API.md changed (its section 13) |
| `sirat_requirements.txt` | Context on what users do. It was written from an engineer's demo: read it for what users need, not as a list of calls to copy | Method names, shapes |

Precedence when they disagree: **STATION_API.md / `station_protocol` > the fake's behaviour > API_DESIGN.md > the
legacy code**. The legacy code wins only on facts about the hardware (a function's real name, argument order,
units, what it raises). Record those, and if they conflict with the contract, raise them (section 6).

## 2. How to approach it

1. **Read the contract first, the legacy code second.** Know what each method must do before looking at how the
   old code did something similar; otherwise its shapes leak into yours.
2. **Build a call map from the legacy code** (`docs/LEGACY_CALL_MAP.md` in your repo). One row per Station API
   method (and per op type in STATION_API.md section 11):

   | Method | Legacy location | Library call(s), in order | Arguments and units | Returns | Raises | Side effects, timing, threads |
   |---|---|---|---|---|---|---|

   Find every place the old code does that job; there may be several, and they may disagree. Note the
   differences. Typical things to pin down:
   - `dut.rm.readByName` / `writeByName`, and how names are spelled;
   - `rpc_io.Connect()`, and what a reconnect needs;
   - `reset_and_download_lpw_phy`, `load_wifi_phy` and the TestInputs override keys;
   - `pti_prs_module` per chip family;
   - `SwitchUtils` / `BenchUtils` path names and roles;
   - the signal generator driver (Hz vs MHz, waveform files);
   - the chamber's stability logic;
   - the ECA's channel names, sample format, scaling to mV and byte order;
   - how `dut_control` is introspected, and how the console namespace was built;
   - which exceptions mean a lost link, a firmware assert or a bad argument.
3. **Mark each row** *confirmed* (you found the call and its behaviour), *unclear* (several versions, or behaviour
   you can't tell from code) or *missing* (the old code never did it: `dut.probe`, `dut.reconnect` without a
   full connect, `call.late`, paged ECA results, console sessions...). Missing rows are expected: the contract
   adds things the old GUI never had. Design those from the contract, not from the old code.
4. **Then build the service** (section 3), slice by slice (section 7), running the conformance suite as you go.

## 3. What to build

The service lives in the station repository, next to the shared packages, not in the GUI's repository. The GUI
never imports the service, and the service never imports the GUI. The layout follows the debug harness migration
design; the folder names below are what matters, and the file names are suggestions:

```
labate-station/                   (uv workspace)
  protocol/                       station_protocol, moved from the GUI repo; published, every tool pins it
  station/src/station/
    core/                         the hardware: DUT library and instrument adapters, real and simulated
    service/
      server.py                   sockets, framing, connections, the envelope, per-connection seq, topics
      router.py                   finds the method by wire name, checks params, checks requires, runs it
      runtime/                    built once, used by every group:
        facts.py                    the facts, reset rules, status.changed on every change
        requires.py                 Method.requires checked against the facts (port src/sibench_ui/core/requires.py)
        locks.py                    one lock per position and per instrument; busy with the holder's request_id
        timeouts.py                 _meta.timeout_ms -> timeout {still_running, request_id} -> call.late
        activities.py               starting -> executing -> done, abort points, activity.finished exactly once
        watches.py                  registers.watch ticks, coalescing, no seq for dropped watch events
      groups/                     one module per method group: thin handlers calling core/
        system.py  dut.py  registers.py  memory.py  rf.py  instruments.py
        automation.py  activity.py  tests.py  advanced.py
        session.py                  (the debug harness's own group, when it's designed)
    client/                       station_client, moved from the GUI repo
  tests/contract/                 the conformance suite, moved from the GUI repo
```

**Build the cross-cutting parts once, in `service/`, not inside a group.** Timeouts and `call.late`, activities,
requires, locks, topics, `seq` and watch coalescing are how the service behaves for every tool. If SiBench's group
modules implemented them, the debug harness would not get them. A group module only has its handlers, each
declaring what the runtime needs to know: which lock it takes, and whether it starts an activity. Its name,
parameters, result and `requires` already come from the `station_protocol` `Method`, so don't restate them.

```python
# station/service/groups/registers.py (sketch)
from station_protocol import registers as wire

@handler(wire.METHODS, "registers.write", lock="position")      # params already checked, requires already met
def write(ctx, pos, name, value, confirm, verify) -> wire.WriteResult:
    return ctx.core.registers(pos).write(name, value, confirm=confirm, verify=verify)
```

The router uses `station_protocol.method.check_params` (strict, refuses unknown params, fills defaults) and
answers with `wrap_result`. Validate what you send against the same types in your tests (section 5).

Hard rules:

- **The contract changes only in `station_protocol`.** No method, field, envelope key or error code exists
  anywhere else. If the hardware makes something in the contract impossible or wrong, raise it first
  (section 6). When it's agreed, change `station_protocol`, regenerate the reference, and bump `PROTOCOL_VERSION`
  if the change breaks clients.
- **Never coerce silently.** `"5"` is not 5. Validate first, then act.
- **Map every library exception** to a contract code at the group's boundary. An exception that escapes is a bug
  (`internal` with a trace id), not something a client can act on.
- **Don't block a connection's reader** on hardware: long calls run while other positions' calls proceed.
- **Units and formats on the wire are the contract's** (Hz, mV little-endian int16, base64, unix-seconds `ts`,
  ISO `Fault.at`), whatever the library uses internally. Convert in the adapter.
- Keep `sys.hello` cheap and lock-free: every client uses it as a heartbeat.
- `core/` never imports `station_protocol`, `service/` or Qt; `service/` never imports Qt.

## 4. A simulation mode

Give the service a mode that runs with simulated adapters, seeded with the **reference fixture** the fake carries.
You may port these, or load them from a data file you generate from them:
- the chip in `src/sibench_ui/gateway/fake/chip.py`: the LION family, its peripherals, registers, fields and access
  types;
- the bench in `gateway/fake/instruments.py`: `siggen1`, `switch1` with `TX_PATH`, `chamber1`, and `eca1` with its
  channels and triggers;
- the memory map in `gateway/fake/memory.py`;
- the DUT control API in `gateway/fake/dut_api.py`;
- the sample tests in `gateway/fake/station_tests.py`.

That mode is how the conformance suite runs against you in CI. It also lets the GUI run against your real service
without hardware (`sibench --backend api --port <yours>`).

## 5. Proving conformance

1. **Run the contract suite against your service** (simulation mode, reference fixture):

   ```bash
   SIBENCH_STATION=127.0.0.1:47800 uv run pytest tests/contract -rs
   ```

   It drives your service through `station_client` over TCP, and checks every reply and event against
   `station_protocol`'s types. Every test that doesn't need the fake's knobs must pass; the rest skip and say why.
   Against the fake itself all of them pass: run `uv run pytest tests/contract` to see what passing looks like.
2. **Move the suite into your repository.** It imports only `station_protocol` and `station_client`, except
   `LocalStation` in its `conftest.py`, which starts this repository's fake. Replace that class with one that
   starts your simulation mode, and make `on_fake` call your simulation's knobs. The skipped tests then run too:
   forcing a timeout followed by `call.late`, a slow call, provoking a DUT drop, and checking that a closed
   connection's watches and sessions end.
3. **Validate everything you send** against `station_protocol` in your own tests (every reply's `result`, every
   event's `data`), with `station_protocol.method.read_result` and `station_protocol.validate.validate`.
4. **Compare with the golden examples.** Every example in STATION_API_REFERENCE.md is what the fake sends for the
   reference fixture. In simulation mode your service should send the same shapes and, where the fixture
   decides them, the same values.
5. **Test what the fake doesn't model**:
   - the locks (`busy`);
   - the 2 s disconnect debounce;
   - watch coalescing, and `seq` (no `seq` for dropped watch events);
   - several clients at once (the GUI and the debug harness together);
   - a call that times out while holding a lock.
6. **Run the real GUI against you**: `python -m sibench_ui --backend api --host 127.0.0.1 --port 47800`. Connect,
   read and write a register, start a watch, run an action, open the console, take an ECA capture.

## 6. When the contract and the hardware disagree

Don't work around it in silence and don't change the shape. Write it down in `CONTRACT_QUESTIONS.md` in your repo:

```
## <method or area>: <one-line problem>
Contract says:   <quote STATION_API.md / station_protocol>
Hardware does:   <what the library really does; legacy file:line as evidence>
Why it matters:  <what breaks or would be wrong for the user>
Proposal:        <the smallest change to the contract, or how to meet it as written>
```

Then carry on with everything else. Expected candidates:
- the open items in STATION_API.md section 14;
- chip families whose PRS module or WiFi support differs;
- instrument models that can't do something the contract assumes;
- library calls that can't honour a timeout or an abort point.

## 7. Build order

Each slice leaves the GUI usable for more pages. Run the conformance suite after each.

| Slice | Methods | GUI pages that work after it |
|---|---|---|
| 1. Wire and state | the server and router on `station_protocol` (framing and envelope come with it), `sys.hello`, `sys.subscribe`, `sys.status`, `status.changed`, `log.line`, requires, facts | the app connects to the station |
| 2. Connect and registers | `dut.connect/reconnect/disconnect/probe/info/set_rpc_timeout`, `dut.disconnected`, `registers.tree/read/read_many/write/write_field`, locks, timeouts, `call.late` | Registers, connection sheet, hardware configuration, system info, dumps, Read All, Radio Calculator diff |
| 3. Live values | `registers.watch/unwatch`, coalescing | Watch list, data logger |
| 4. Activities | `automation.seq.run` and every op, `activity.abort`, `sys.recover`, fault | Actions, Sequences |
| 5. Radio | `dut.load_phy`, `rf.prs_signals`, `rf.prs_route` | Radio and PHY |
| 6. Advanced | `advanced.*`, `memory.*` | Console, custom functions, DUT control explorer, memory viewer |
| 7. Instruments | `instruments.*`, `rf.paths/connect/disconnect` | Instruments |
| 8. Tests | `tests.list`, `tests.run` (a proposal: confirm the open questions first, with the debug harness's test runs) | Tests |

## 8. Done means

- Every method in `station_protocol.catalog` is implemented, and the conformance suite passes against simulation
  mode.
- Your own tests cover the skipped contract cases and the rules the fake doesn't model (section 5).
- Every reply and event validates against `station_protocol`.
- `docs/LEGACY_CALL_MAP.md` has a row per method and op. Each is *confirmed*, *unclear* (with what's unclear) or
  *missing* (with how you built it instead).
- `CONTRACT_QUESTIONS.md` lists every disagreement, each with a proposal.
- The real GUI runs against your service in simulation mode, and every page in the build order works.
- On real hardware, slices 1–2 are checked on a station, and what couldn't be checked is listed.
