# SiRAT Station API — specification (protocol 2)

The contract between the **station service** (the process that owns a test station's hardware: up to four DUT
positions and the bench instruments) and every tool that talks to it. The SiRAT GUI is one such tool; the debug
harness is another. They all speak this one API.

| Document | What it is | Authority |
|---|---|---|
| **This file** | The rules: protocol, state, locking, timeouts, activities, what every method does | Normative |
| `src/station_protocol/` | The contract as code: framing, envelope, error codes, validation, and one module per method group (parameters with ranges, result, `requires`, types, events) | Normative; the two files below are generated from it |
| [STATION_API_REFERENCE.md](STATION_API_REFERENCE.md) | Every method's exact parameters, result and real example JSON; events; types | Normative, generated from code |
| [station_api.schema.json](station_api.schema.json) | The same shapes as JSON Schema 2020-12 | Normative, generated from code |
| `src/station_client/` | A client any tool can use: the connection, reconnecting, the heartbeat | Reference client |
| `tests/contract/` | The conformance suite: drives a station through `station_client` and checks every reply and event against `station_protocol` | Conformance |
| `src/sirat_ui/gateway/fake/` | The fake station: a working implementation of this spec, in memory | Reference behaviour, except what it doesn't model (below) |
| [API_DESIGN.md](API_DESIGN.md) | Revision 2 of the design, with the reasoning behind it | Background; this file wins |

If this file and the generated reference disagree, the reference is what the code really sends and accepts (a test
keeps it in step); report the difference. Words like **must** are requirements on the service.

**Where the contract lives.** `station_protocol` and `station_client` are in this repository for now, but they
import nothing of the GUI (a test checks it), and the conformance suite uses only them. They are meant to move to
the station service's repository, where `station_protocol` is published as a package. Each tool, this GUI
included, then depends on it and pins a version range (`station-protocol>=2,<3`). The JSON Schema and the
reference become release files of that package. A tool's own group of methods (the debug harness's `session`, for
example) is one more module in `station_protocol`, added to `catalog.GROUPS`. Changing a group never touches
another.

The fake runs in memory with no real concurrency, so it doesn't model four rules here: the position and
instrument **locks** (`busy`), the **2 s debounce** before `dut.disconnected`, **watch coalescing**, and `claim`.
For those, this file is the only reference.

---

## 1. The system

SiRAT is a register access and bench-control tool for validation engineers testing Silicon Labs chips. An engineer
sits at a station PC with DUTs (devices under test) on up to four positions and shared bench instruments: a
signal generator, an RF switch, a temperature chamber and an ECA (a multi-channel capture instrument).

```
 SiRAT GUI (PyQt5/QML)  ──TCP loopback, JSON-RPC 2.0──►  station service  ──►  DUT library (rm, rpc_io,
   all presentation, files,                               facts, locks,          dut_control, configurators,
   code generation, history                               activities, events     pti_prs) per position
                                                                          ──►  instrument drivers
```

Other tools connect to the same service the same way, and may be connected at the same time as the GUI.

The service owns all hardware access and all station state. The GUI owns everything about presentation and the
user's own files (actions, sequences, notes, formulas, favorites, history, dumps, sessions, settings). The GUI never
imports the DUT library or instrument drivers; the service never reads the user's files (code it needs, such as a
custom function's body, is sent in the call).

| GUI feature | Uses | GUI-only part |
|---|---|---|
| Connect / reconnect / disconnect, recovery dialog | `dut.connect`, `dut.reconnect`, `dut.disconnect`, `dut.disconnected` | dialog debounce |
| Hardware configuration, test connection, system info | `dut.probe`, `dut.set_rpc_timeout`, `dut.info` | the settings file |
| Register tree, detail, read, write, confirm, verify | `registers.tree/read/write/write_field` | search, notes, formulas, history, formats |
| Dumps, Read All, Radio Calculator diff, logger polling | `registers.read_many` | CSV, comparison, `.cfg` parsing |
| Watch list, data logger | `registers.watch/unwatch`, `registers.watch` events | plots, CSV export |
| Memory viewer | `memory.read/write` | hex formatting |
| PHY loading, PRS routing | `dut.load_phy`, `rf.prs_signals`, `rf.prs_route` | forms, packet visualizer, port/channel check |
| RF switch, signal generator, chamber, ECA | `rf.*`, `instruments.*` | plots, markers, measurements, export |
| Actions, sequences | `automation.seq.run`, `activity.abort`, `activity.*` events | the files, editing, code generation |
| Custom functions, Python console, DUT control explorer | `advanced.*` | editor, history, argument parsing |
| Test execution | `tests.list`, `tests.run` | selection, export |

## 2. Transport

- TCP on loopback. Port from the workspace config; default **47800**. One service per station.
- Each message is a **frame**: a 4-byte big-endian unsigned length, then that many bytes of UTF-8 JSON.
  Maximum body **16 MiB** (16 777 216 bytes). A peer that receives a larger length **must** close the connection
  (the stream can't be resynchronised). A result too big for one frame is answered with `internal`.
- Requests, replies and events share one connection, in both directions, with no ordering between replies.
- Several clients may connect at once. Each connection has its own subscriptions and event counter.
- No authentication and no tokens for now (loopback only; see open items).

## 3. Messages (JSON-RPC 2.0)

```
request       {"jsonrpc":"2.0", "id":17, "method":"registers.read",
               "params":{"pos":1, "name":"CMU.CLKEN0", "_meta":{"timeout_ms":5000}}}
reply         {"jsonrpc":"2.0", "id":17, "result":{"value":3}}
error reply   {"jsonrpc":"2.0", "id":17, "error":{"code":-32001, "message":"DUT 1 isn't ready for registers.read",
                                                   "data":{"reason":"wrong_state", "missing":["dut"]}}}
event         {"jsonrpc":"2.0", "method":"registers.watch", "params":{"seq":912, "data":{...}}}
```

- **`id`** is an integer or string chosen by the client, unique among its calls in flight. Replies carry it back
  and may arrive in any order.
- **`params` is always an object** of named parameters. Positional (array) params are `-32602`.
- **`_meta`** inside `params` is reserved for call options. Today: `timeout_ms` (integer, default the RPC timeout
  setting, 5000 ms). The service removes `_meta` before validating the method's parameters.
- **Results are always JSON objects.** A model result is its fields (`dut.info` → `{chip, revision, hw, rta, app}`);
  a single value or list is wrapped (`registers.read` → `{"value": 3}`, `rf.paths` → `{"names": [...]}`); a call
  that starts an activity returns `{"activity_id": ...}`; a call with nothing to return returns `{}` (*Empty*).
  The wrapping key of every method is in the reference.
- **Errors**: `code` is the JSON-RPC integer, `message` is for people, `data.reason` is the Station API code
  (section 10) and the rest of `data` is that code's detail. Clients branch on `data.reason`, never on `message`.
- **Events** are notifications: no `id`, the event name as `method`, `params.seq` and `params.data` (section 9).
- **Batches** (a JSON array) aren't supported: one `-32600` error with `id: null`.
- A request **without** `id` is run and gets no reply. Clients don't send them.
- Malformed JSON: `-32700`, `id: null`. Not a JSON-RPC request: `-32600`. Unknown method: `-32601`.

### Validation and evolution

- The service **must** validate `params` against the method's schema **before** doing anything: types, ranges and
  allowed values, and **unknown parameters are an error** (`invalid_params`, `data.param` names the first bad one,
  e.g. `"pos"`, `"ops[1].value"`). Nothing is coerced: `"5"` or `true` where a number belongs is an error; a whole
  number is fine where a float belongs.
- Clients **ignore unknown keys** in results and events, so the service may add fields without a new protocol
  number. Removing or renaming a field, or changing its type or meaning, needs a new protocol number.

### Encoding conventions

| Kind | On the wire |
|---|---|
| Names | `snake_case` keys; methods `domain.verb` or `domain.sub.verb` |
| DUT position | `pos`, integer 1–4 (`position` inside `PositionFacts`) |
| Instrument | `id` in params (`"siggen1"`), `instrument_id` in results and events |
| Register / field names | `"PERIPHERAL.REGISTER"`, field as a separate `field` param or `"PERIPHERAL.REGISTER.FIELD"` in name lists |
| Integers | JSON numbers; register values 0..2³²−1, addresses 0..2³²−1 |
| Times | event `ts` and similar: unix seconds as a number; `Fault.at`, `server_time`: ISO 8601 UTC string |
| Frequencies | Hz on the wire (the GUI shows MHz) |
| Raw bytes | base64 strings (`memory.read` data, ECA samples) |
| Enums | lower-case strings (`"rw"`, `"idle"`, `"signal_generator"`) |
| Tagged unions | `kind` (`PhySpec`) or `type` (`automation.seq.run` ops) |
| Optional | a nullable field is `null`; an optional key in an event may be left out (section 9) |

## 4. Connection lifecycle

```
connect ─► sys.hello(client, protocol) ─► sys.subscribe(topics) ─► sys.status() ─► calls … ◄─ events
```

1. **`sys.hello`** — the client says who it is (`client`: `"sirat-gui"`, `"debug-harness"`...) and which protocol
   it speaks (`2`, `station_protocol.PROTOCOL_VERSION`); both are required. The service answers its `release_id`,
   its `protocol` and `server_time`. A client and service with different protocol numbers aren't compatible; the
   GUI shows the release in its status bar.
2. **`sys.subscribe(topics)`** — which events this connection gets: any of `status`, `activity`, `watch`, `log`.
   A new connection has **no** topics. A second call replaces the set. An unknown topic is `invalid_params`.
3. **`sys.status`** — the full state snapshot (section 5). The GUI calls it after subscribing, after a reconnect,
   and whenever an event `seq` gap means it may have missed a `status.changed`.

**When a connection closes**, the service ends the watch subscriptions and closes the console sessions that
connection opened (and updates `watching`). It does **not** stop activities: they run to the end and send
`activity.finished` to whoever is subscribed. DUT connections and instrument state stay as they are.

`station_client.Link`, which the GUI uses, reconnects by itself after a drop (backoff 0.5 s doubling to 10 s) and
subscribes again; the GUI then refetches status. While connected it sends `sys.hello` after 15 s of silence as a
heartbeat and treats no answer within ~3 s as a dead link, so `sys.hello` must stay cheap and must not take a
position lock.

## 5. State: facts

The service keeps **facts** for each DUT position and each instrument. They're the only shared state the GUI
reads, and every change is announced with `status.changed` (topic `status`) carrying the full `StationStatus`.

```
StationStatus   { release_id: str, positions: [PositionFacts ×4], instruments: [InstrumentFacts], claim: str|null }
PositionFacts   { position: 1..4, dut_connected: bool, phy: str|null, watching: bool, rf_path: str|null,
                  activity: "idle"|"starting"|"executing"|"aborting"|"done", fault: Fault|null }
Fault           { cause: str, detail: str, at: ISO-8601 }        # cause: data.cause of the error, else its code
InstrumentFacts { id: str, kind: "signal_generator"|"rf_switch"|"chamber"|"eca", connected: bool,
                  model: str, activity: str }
```

- `positions` always has all four positions. `claim` is who holds the station exclusively (null today).
- Facts are updated **before** the reply that caused them is sent, so a `sys.status` right after any reply is
  already right. A `hardware_error` or `dut_disconnected` updates the facts before its error reply too.
- **Reset rules.** A DUT disconnect (asked for or detected) clears `phy`, `watching` and `rf_path`, ends that
  position's watches and closes console sessions bound to it. Loading a PHY changes nothing else. An instrument
  that drops ends its activity with `instrument_error`.
- **Fault.** A hardware error during an activity on a position sets that position's `fault`. Until `sys.recover`
  clears it, calls that require `no_fault` are refused.

### Requires

Each method lists **tags** that must hold, checked before it runs. The GUI enables buttons from the same table
(`src/sirat_ui/core/requires.py`), so a stale GUI is still safe. A call whose tags don't hold fails with
`wrong_state` and `data.missing: [tags…]` (always tags, never fact names).

| Tag | Holds when |
|---|---|
| `dut` | the position's `dut_connected` |
| `phy` | the position's `phy` is set (no method needs it today) |
| `idle` | the position's `activity` is idle — or, for a call with an instrument `id`, that instrument's |
| `no_fault` | the position's `fault` is null |
| `instrument:<kind>` | with an `id`: that instrument is connected. Without one: some instrument of that kind is |

| Method | Requires |
|---|---|
| `dut.connect`, `dut.reconnect` | `no_fault` |
| `dut.info`, `registers.tree`, `registers.read`, `registers.read_many`, `registers.watch`, `memory.read`, `rf.prs_signals`, `rf.prs_route`, `advanced.console.open`, `advanced.console.exec`, `advanced.dut_control.describe` | `dut` |
| `dut.load_phy`, `registers.write`, `registers.write_field`, `memory.write`, `advanced.custom_function`, `advanced.dut_control.invoke` | `dut`, `idle` |
| `automation.seq.run`, `tests.run` | `dut`, `idle`, `no_fault` |
| `rf.paths`, `rf.connect`, `rf.disconnect` | `instrument:rf_switch` |
| `instruments.siggen.get/waveforms/trigger/rf` | `instrument:signal_generator` |
| `instruments.siggen.set` | `instrument:signal_generator`, `idle` |
| `instruments.chamber.read` | `instrument:chamber` |
| `instruments.chamber.set_temp`, `instruments.chamber.wait_stable` | `instrument:chamber`, `idle` |
| `instruments.eca.sources` | `instrument:eca` |
| `instruments.eca.capture` | `instrument:eca`, `idle` |
| everything else | — |

Order of checks: frame → envelope → method exists → params valid → instrument `id` exists (`not_found`) →
requires (`wrong_state`) → lock (`busy`) → run.

## 6. Concurrency and timeouts

- **One lock per DUT position and one per instrument.** A call that touches a position's hardware holds that
  position's lock for its duration; an instrument call holds the instrument's. A call that can't get the lock at
  once fails with `busy` and `data.request_id` of the call holding it (it doesn't queue).
- Calls on different positions or instruments run concurrently. Replies may overtake each other.
- **Timeouts.** A call still running after `_meta.timeout_ms` is answered `timeout` with
  `data: {still_running: true, request_id: <this call's JSON-RPC id>}`. The hardware call is **not** cancelled: it
  keeps running and keeps its lock. When it ends, the service sends **`call.late`** to that connection with the
  same `request_id` and either `ok: true, result: <the result, in the method's result shape>` or
  `ok: false, error: <error object>`. This is how the GUI learns whether a timed-out write happened.
- `dut.set_rpc_timeout(seconds)` sets every DUT's RPC timeout **and** the default `timeout_ms` for calls.
- Activities (section 7) return at once, so they never time out as calls.

## 7. Activities

Long operations are **activities**: the call returns `{activity_id}` at once and the work reports through events.

| Activity | Started by | Belongs to |
|---|---|---|
| A run of ops | `automation.seq.run` | position (`pos`) |
| A run of station tests | `tests.run` | position |
| Wait for the chamber to stabilise | `instruments.chamber.wait_stable` | instrument (`instrument_id`) |
| ECA capture | `instruments.eca.capture` | instrument |

- A position or instrument has **at most one activity**. While it runs, its `activity` fact is `executing` (via
  `starting`; `aborting` after an abort) and calls requiring `idle` on it are `wrong_state`.
- **`activity.progress`** as the work advances: `step` of `total`, a `message`, and for `seq.run` the op's `group`
  (the user's action it came from); for `tests.run` the test id as `group`, and once a test ends its `result`.
- **`activity.finished`** exactly **once** per activity — after success, failure, abort, an instrument drop, or a
  service restart: `ok`, `results[]` (one per op or test that ran), `error` (what ended it, if not ok) and a
  kind-specific `result` (`{capture_id}` for an ECA capture).
- **`activity.abort(activity_id)`** is cooperative: it takes effect at the next wrapped hardware call, ends in the
  safe state, and the activity finishes with `ok: false, error: aborted`. Aborting an unknown or finished activity
  is not an error (the GUI may abort twice).
- A `hardware_error` during a position's activity sets that position's `fault` (section 5).
- Activities survive the client disconnecting.

## 8. Methods

Each method's exact parameters, defaults, ranges, result shape and examples are in the
[reference](STATION_API_REFERENCE.md). Below is what each must **do**. "Errors" lists codes beyond the ones every
method can return (`invalid_params`, `wrong_state` per section 5, `busy`, `timeout`, `internal`); "Changes" lists
facts changed and events sent.

### sys

| Method | Does | Errors | Changes |
|---|---|---|---|
| `sys.hello(client, protocol)` | Identifies both ends; `{release_id, protocol, server_time}`. Cheap, no lock (heartbeat). | — | — |
| `sys.subscribe(topics)` | Sets this connection's topics (section 4). | unknown topic → `invalid_params` | — |
| `sys.status()` | The `StationStatus` snapshot. | — | — |
| `sys.recover(pos)` | Applies the safe state to the position and clears its `fault`. | — | `fault` null, `activity` idle; `status.changed` |

### dut

| Method | Does | Errors | Changes |
|---|---|---|---|
| `dut.connect(pos, config_type, config_file, rpc?)` | Bench setup for the position from the config (`config_type` `EFR32`/`EFX`, `config_file` `""` = station default), then the RPC connection to the DUT. `rpc` null = the workspace config's address; else connect there, for this connection only. Sends `log.line` progress with `source: "dut.connect"` and `pos` while it runs. Result `{chip: {part, revision, family}, rpc: {host, port}}` (where it was actually reached). | address unreachable → `timeout`; library → `hardware_error` | `dut_connected` true; `status.changed`, `log.line` |
| `dut.reconnect(pos)` | RPC only (`rpc_io.Connect()`), keeping the bench setup: recovery after a firmware assert. | position never connected since the service started → `not_found` | `dut_connected` true; `status.changed` |
| `dut.disconnect(pos)` | Closes the DUT connection. | — | reset rules (section 5); `status.changed` |
| `dut.probe(pos, rpc, timeout_s)` | Can that address be reached? **Never** connects or disconnects anything, so testing a setting can't drop a live connection. `rpc` null = the workspace address for `pos`. Unreachable is `{ok: false, detail}`, not an error. No `dut` requirement. | bad `rpc` → `invalid_params` | — |
| `dut.info(pos)` | System information: `chip`, `revision`, `hw{}` (device-info words such as `PART_NUMBER`, `UNIQUE_ID`), `rta{host, port, timeout_s}`, `app{name, version, build_time}` when the firmware reports one. | — | — |
| `dut.load_phy(pos, phy)` | `phy` is `{kind: "lpw", name}` → `reset_and_download_lpw_phy(name)`; or `{kind: "wifi", config: WifiPhyConfig}` → builds the TestInputs overrides and calls `load_wifi_phy`. Result `{name, function, overrides: [[key, value]…]}`: what it called and the overrides it set. | WiFi on a non-Everest DUT, channel outside the standard's band → `invalid_params`; library → `hardware_error` | `phy` set; `status.changed`, `log.line` |
| `dut.set_rpc_timeout(seconds)` | Station-wide: every DUT's RPC timeout and the default `timeout_ms`. 1–300 s. | — | — |

`WifiPhyConfig`: `mode` RX/TX, `standard` (802.11b/g/a/n/ac/ax/be), `channel` (in the standard's band),
`power_mode` HP/LP/MP (MP only for ax/be), `rate`, `phy_name`, `tx_params` {`pkt_length` 1–65535, `num_pkts`
0–1 000 000 (0 = continuous), `transmit_mode`, `aggr_enable`} only for TX, `advanced` {`ppdu_type`, `gi_ltf`,
`dcm` bool, `bandwidth`} only for ax/be.

### registers

| Method | Does | Errors | Changes |
|---|---|---|---|
| `registers.tree(pos)` | Every peripheral, register and field of the connected chip: `{tree_id, peripherals}`. Peripherals carry `critical` (writes need `confirm`: CMU, EMU, MSC, SMU) and `read_sensitive` (reading has side effects: USART, I2C, SPI); registers `address`, `width`, `access`, `reset_value` (null if unknown), fields `lsb`, `width`, `access`, `enums`. `tree_id` is a content hash; the GUI caches by (chip, revision, `tree_id`). | — | — |
| `registers.read(pos, name)` | One register → `{value}`. A single read of a read-sensitive register **is** allowed (the user asked for exactly that one). | unknown name → `not_found`; `wo`/`w1`/`unknown` access → `access_denied`; link lost → `dut_disconnected` | — |
| `registers.read_many(pos, names, include_read_sensitive=false)` | Bulk read → `{items: [{name, value, error}]}` in the order asked. One bad register doesn't fail the call: its item has `value: null` and an `error` object. | per item: `read_sensitive` (unless opted in), `not_found`, `access_denied` | — |
| `registers.write(pos, name, value, confirm=false, verify=true)` | Writes the whole register; with `verify`, reads back. Result `{value_written, value_readback, verified}`. A read-back that differs is `verified: false`, **not** an error (the write happened; the GUI warns). `value_readback` null when the register can't be read. | critical peripheral without `confirm` → `confirmation_required`; not writable (`ro`, `unknown`) → `access_denied`; value doesn't fit `width` → `out_of_range`; `not_found` | — |
| `registers.write_field(pos, name, field, value, confirm, verify)` | Read-modify-write of one field under the position lock. `value` is the field's value; `value_written` is the whole register value written. | as `registers.write`; value doesn't fit the field → `out_of_range` | — |
| `registers.watch(pos, names, interval_s, include_read_sensitive=false)` | Starts a subscription → `{sub_id}`: a `registers.watch` event with all the names' values every `interval_s` (0.1–60). If the client falls behind, keep only the newest values per subscription; dropped ones use no `seq`. Owned by the calling connection. | `read_sensitive`, `not_found` | `watching` true; `status.changed` |
| `registers.unwatch(sub_id)` | Ends a subscription. Unknown id is not an error (it may have ended with a disconnect). | — | `watching` false when the position has no other watch |

Access types: `ro` read-only, `wo` write-only, `rw` read-write, `w1` write-once, `rw1` read-write-once, `unknown`.

### memory

| Method | Does | Errors | Changes |
|---|---|---|---|
| `memory.read(pos, address, size)` | `size` 1–4096. Aligns the start down and the end up to 4 bytes; result `{address, data}`: the aligned start actually read and the bytes (base64). | unmapped → `out_of_range` | — |
| `memory.write(pos, address, value, size)` | `size` 1, 2 or 4. Read-modify-write of the aligned 4-byte word under the position lock (atomic for unaligned writes). Result `{address, value_written, value_readback}`. The GUI confirms every write and refuses one that crosses a word. | flash → `access_denied`; value doesn't fit / unmapped → `out_of_range` | `log.line` |

### rf

| Method | Does | Errors | Changes |
|---|---|---|---|
| `rf.paths()` | The RF switch's path names (switch configuration) → `{names}`. | — | — |
| `rf.connect(pos, path)` | Connects a switch path to the position. | unknown path → `not_found`; `instrument_error` | `rf_path` set; `status.changed`, `log.line` |
| `rf.disconnect(pos)` | Disconnects the position's path. | `instrument_error` | `rf_path` null; `status.changed`, `log.line` |
| `rf.prs_signals(pos)` | The PRS signals the chip family's `pti_prs_module` defines → `{family, module, signals}` (sorted). | — | — |
| `rf.prs_route(pos, route)` | `route {signal, pin, channel}`: routes an internal signal to a GPIO pin `PA0`–`PD7` over PRS channel 0–11; `signal: "DISABLE"` removes the route on that channel. One route per channel (a new one replaces it). | port A/B with channels 6–11, or C/D with 0–5 → `invalid_params` | `log.line` |

### instruments

| Method | Does | Errors | Changes |
|---|---|---|---|
| `instruments.list()` | `{instruments: [InstrumentFacts]}` (also in `sys.status`). | — | — |
| `instruments.connect(id, address?)` | Connects an instrument that dropped; `address` null = its configured address. | `not_found`, `instrument_error` | `connected` true; `status.changed` |
| `instruments.siggen.get(id)` | What the generator is loaded with: `SiggenConfig {sg_type, input_config_name, frequency_hz, power_dbm, overrides}`. | `instrument_error` | — |
| `instruments.siggen.set(id, config)` | Applies it. `power_dbm` −150–30; `input_config_name` one of the waveforms. | out of range, unknown waveform → `invalid_params`; `instrument_error` | `log.line` |
| `instruments.siggen.waveforms(id, reload=false)` | The waveform files → `{names}`; `reload` rescans them. | `instrument_error` | — |
| `instruments.siggen.trigger(id, mode)` | Starts the waveform: `infinite` or `single`. | `instrument_error` | `log.line` |
| `instruments.siggen.rf(id, on)` | RF output on/off. | `instrument_error` | `log.line` |
| `instruments.chamber.read(id)` | `{actual_c, target_c, stable}`. The GUI polls it at the user's interval while the page is visible. | `instrument_error` | — |
| `instruments.chamber.set_temp(id, celsius)` | Returns when the setpoint is accepted, not when it's reached. | `instrument_error` | `log.line` |
| `instruments.chamber.wait_stable(id, tolerance_c=0.5, hold_s=60, timeout_s=3600)` | Activity: done once the reading has stayed within `tolerance_c` of the setpoint for `hold_s`. Progress about once a second; abortable. | in `activity.finished.error`: `timeout`, `aborted`, `instrument_error` | instrument `activity`; `activity.*` |
| `instruments.eca.sources(id)` | `{channels, triggers}`; `"immediate"` is always allowed as a trigger. | `instrument_error` | — |
| `instruments.eca.capture(id, spec)` | Activity: arm, wait for the trigger, capture, upload. `spec {channels, trigger, edge rising/falling/either, sample_rate_hz, duration_s, pretrigger_pct 0–90}`; 2 to 1 000 000 samples per channel. `activity.finished.result` is `{capture_id}`. Keep the capture until its last page is read, or for 1 hour. | unknown channel or trigger, too many samples → `invalid_params` | instrument `activity`; `activity.*` |
| `instruments.eca.result(capture_id, offset=0, count=65536)` | One page: `{meta {spec, started_at, sample_count, chip, pos}, offset, count, channels {name: base64}, more}`. Samples are **little-endian int16, in mV**. `more: false` on the last page. | unknown or expired capture → `not_found` | — |

### automation, activity

| Method | Does | Errors | Changes |
|---|---|---|---|
| `automation.seq.run(pos, ops, stop_on_error=true)` | Activity: runs the ops in order (section 11). All ops in one run share one Python namespace. One `activity.progress` per op, echoing its `group`. With `stop_on_error` the first failing op ends the run; without it, failures are recorded in `results` and the run goes on. | ops validated up front: unknown `type`, missing field, empty list → `invalid_params`; in `activity.finished.error`: the failing op's error, `aborted` | position `activity`; `activity.*` |
| `activity.abort(activity_id)` | Cooperative abort (section 7). | none: unknown/finished ids are ignored | — |

### tests (frontend proposal, not agreed)

| Method | Does | Errors | Changes |
|---|---|---|---|
| `tests.list()` | `{tests: [{id, name}]}`. | — | — |
| `tests.run(pos, test_ids)` | Activity: runs the tests in the order given; each test is one call to its `execute()`. `activity.progress` as each test starts (`message` = name, `group` = id) and again as it ends with `result {id, passed, started, duration_s, notes, output[]}`. `finished.ok` false if the run ended early; `results` holds every test that finished. | empty list, unknown id → `invalid_params`; in `finished.error`: `aborted`, `dut_disconnected` | position `activity`; `activity.*` |

### advanced

| Method | Does | Errors | Changes |
|---|---|---|---|
| `advanced.console.open(pos)` | A Python namespace holding `dut` and the test utilities (and `self` in debug mode) → `{session_id}`. Kept until closed, the client disconnects, or the DUT disconnects. | — | — |
| `advanced.console.exec(session_id, code, mode="auto")` | Runs code in the session. `auto` tries `eval`, falls back to `exec` on `SyntaxError`. Result `ExecResult {stdout, stderr, result_text, error}`: `result_text` is the value's repr (null when none); a Python exception is a **successful** reply with `error {type, message, text}` set. | ended session → `not_found` with `data.session_id` (the GUI reopens once and retries) | — |
| `advanced.console.names(session_id)` | The namespace's public names → `{names: [{name, type, doc}]}` for Help. | `not_found` | — |
| `advanced.console.close(session_id)` | Drops the namespace. Unknown id is not an error. | — | — |
| `advanced.custom_function(pos, name, code, session_id?)` | Runs `code` wrapped in a function (a top-level `return` works) → `ExecResult`. With `session_id` it runs in that namespace and stores `result_<name>` and `last_dut_api_result` there; without, in a fresh one. | session → `not_found` | `log.line` |
| `advanced.dut_control.describe(pos)` | The `dut.dut_control` API → `ApiTree {packages [{name, modules [{name, path, methods [{name, path, signature, doc, params [{name, annotation, default_repr, required}]}]}]}]}`: packages Common, Host, LPW, WiFi; classes preferred over modules; private methods skipped; the injected `dut` parameter left out; `doc` is the first docstring paragraph. | — | — |
| `advanced.dut_control.invoke(pos, path, args, kwargs)` | Calls the method, injecting `dut` when it takes it → `{result_text, result_json, result_type}`. `result_text` is for reading (a list or tuple: length and first 10 items; a dict: all pairs; an object: type and public attributes); `result_json` the value when it's JSON, else null. | unknown path → `not_found`; arguments don't bind → `invalid_params`; the library raised → `hardware_error` with `data.cause` (`rpc_timeout`, `rpc_transport`, `rail_assert`, `other`) and `data.traceback` | `log.line` |

## 9. Events

| Event | Topic | Data | When |
|---|---|---|---|
| `status.changed` | `status` | `StationStatus` | any fact changes |
| `dut.disconnected` | `status` | `{pos, cause, detected_by}` | the service detects a lost DUT (after a 2 s debounce); facts already reset |
| `registers.watch` | `watch` | `{sub_id, pos, ts, values: [{name, value}]}` | every interval of a subscription |
| `activity.progress` | `activity` | `{activity_id, pos or instrument_id, step, total, message, group?, result?}` | an activity advances |
| `activity.finished` | `activity` | `{activity_id, pos or instrument_id, ok, results, error?, result?}` | exactly once per activity |
| `log.line` | `log` | `{ts, level, source, text, pos?}` | service log lines for the GUI's log panel; `dut.connect` progress |
| `call.late` | (the caller) | `{request_id, ok, result? \| error?}` | a timed-out call finished (section 6) |

- An activity event carries `pos` for a position's activity or `instrument_id` for an instrument's, never both.
  Keys marked `?` are left out when they have no value. `level` is `debug`, `info`, `success`, `warning` or
  `error`.
- **`seq`** is per connection and goes up by exactly one for every event **sent** on it. A gap means events were
  lost, so the client refetches `sys.status`. Watch events dropped by coalescing never consume a `seq`.
- Instrument facts change through `status.changed`; there is no separate instrument event.

## 10. Errors

| `data.reason` | `code` | Meaning | `data` |
|---|---|---|---|
| `wrong_state` | −32001 | Requires unmet | `missing: [tag]` |
| `invalid_params` | −32602 | Schema, range or value check failed | `param` (path of the first bad one) |
| `unknown_method` | −32601 | No such method | — |
| `timeout` | −32002 | Exceeded `timeout_ms` | `still_running`, `request_id` |
| `busy` | −32003 | Position or instrument locked | `request_id` of the holder |
| `claimed` | −32004 | Another owner holds the station | — |
| `confirmation_required` | −32005 | Critical register written without `confirm` | `register` |
| `read_sensitive` | −32006 | Read-sensitive register in `read_many` / `watch` without opt-in | `register` |
| `access_denied` | −32007 | Not readable / writable (register access, flash) | — |
| `out_of_range` | −32008 | Value or address doesn't fit | — |
| `not_found` | −32009 | Register, path, id, session or capture unknown | `session_id` for an ended console session |
| `dut_disconnected` | −32010 | Link to the DUT lost during the call | — |
| `instrument_error` | −32011 | The instrument reported an error | — |
| `hardware_error` | −32012 | The DUT library raised | `cause`, `traceback` where known |
| `aborted` | −32013 | Activity aborted | — |
| `internal` | −32603 | A bug in the service | a trace id |

`-32700` (parse error) and `-32600` (invalid request) carry reason `invalid_params`. Library exceptions are mapped
to these codes at the boundary of each domain; nothing else reaches the client. A `hardware_error` during an
activity sets the position's `fault`; `hardware_error` and `dut_disconnected` update facts before the reply.

## 11. Ops (`automation.seq.run`)

Ops are the steps of the user's saved actions. The GUI expands sequences, copies custom-function code in, and
sends only these shapes (tagged by `type`); each may carry `group`, the action it came from. Field lists are in the
reference under `WireOp`.

| `type` | Fields | Does |
|---|---|---|
| `register_write` | `register`, `value` | writes the whole register; inside a run a critical register is not refused (there's no confirm step) |
| `field_write` | `register`, `field`, `value` | as `registers.write_field` |
| `rf_switch` | `path` | connects the path to the run's position |
| `load_phy` | `phy_name`, `method_name?` | as `dut.load_phy` with an LPW PHY |
| `load_wifi_phy` | `config: WifiPhyConfig` | as `dut.load_phy` with a WiFi PHY |
| `signal_generator` | `instrument_id`, `config: SiggenConfig` | as `instruments.siggen.set` |
| `gfsk_packet` | `code` | runs generated Python that drives the signal generator |
| `custom_function` | `function_name`, `code` | as `advanced.custom_function` in the run's namespace |
| `dut_control_method` | `method_path`, `method_name`, `params{}` | as `advanced.dut_control.invoke` with `kwargs = params` |
| `dut_reconnect` | `description?` | as `dut.reconnect` |
| `prs_route` | `signal`, `pin`, `channel` | as `rf.prs_route` |

## 12. Limits and constants

| What | Value |
|---|---|
| Protocol number | 2 |
| Frame body | ≤ 16 MiB |
| Positions | 1–4 |
| `timeout_ms` default; RPC timeout range | 5000 ms; 1–300 s |
| Watch interval | 0.1–60 s |
| `memory.read` size; `memory.write` size | 1–4096 bytes; 1, 2 or 4 |
| ECA samples per channel; page default; retention | 2–1 000 000; 65 536; 1 h or until last page read |
| Chamber wait defaults | tolerance 0.5 °C, hold 60 s, timeout 3600 s |
| `dut.disconnected` debounce | 2 s |
| GUI heartbeat | `sys.hello` after 15 s silence; dead after ~3 s without reply |

## 13. Decisions in this revision

Where this spec departs from [API_DESIGN.md](API_DESIGN.md) revision 2, and why. The rest of revision 2 stands.

1. **JSON-RPC 2.0 envelope** (protocol 2). The old `{id, ok, result|error}` / `{event, seq, data}` framing is gone;
   integer error codes with the old string code kept as `data.reason`.
2. **Validation policy.** Unknown *parameters* are rejected, but clients ignore unknown keys in results and events,
   so the service can add fields without breaking clients (revision 2 said unknown fields are rejected everywhere).
3. **`tests.list` returns `{tests}`**, like every other list result (revision 2 had a bare list).
4. **Ops are validated before the run starts** against the shapes in section 11, so a bad op fails the call
   instead of failing halfway through a run on the hardware.
5. **`dcm` is a boolean** everywhere on the wire (revision 2 said 0|1; the GUI's action files keep 0/1).
6. **`Fault.at` is an ISO 8601 string** (revision 2: `datetime`, unspecified encoding).
7. **Removed, because nothing uses them:** `sys.describe` (the JSON Schema file covers tooling),
   `activity.status` (the GUI follows events), `instruments.disconnect`, the `instrument.changed` event and the
   `instrument` topic (instrument facts arrive with `status.changed`). Add them back when a client needs them.
8. **`sys.hello`'s `client` and `protocol` are required.** They had the GUI's values as defaults, but the
   contract is shared by every tool, so each says who it is.
9. **One API for every tool, with the longer group names** (`registers`, `tests`, `instruments`...). Other tools
   use these groups too, not short aliases (`reg`, `test`) for the same thing.

## 14. Open items

1. **Read-sensitive registers.** The current rule (single read allowed; `read_many` and `watch` refuse unless
   `include_read_sensitive`) is a placeholder until the validation engineers decide.
2. **`tests.*`** is a frontend proposal: where tests come from (the station or files), what a test sequence is,
   where Notes come from, and whether a failure stops the run.
3. **Debug-mode attach:** whether SiRAT can use a `dut` a paused test already connected.
4. **Authentication:** loopback without auth or tokens, while `advanced.console` runs arbitrary code on a shared
   station. Out of scope for now.
5. **`dut_control` argument types:** JSON only, or do some methods need typed objects?
6. **One service per station** or several (affects `sys.hello` and `claim`).
7. **The `session` group** belongs to other tools: a session groups several test runs (the debug harness). It is
   not SiRAT's `dut.connect`, and SiRAT doesn't call it. Its methods are to be designed with that tool.
8. **`tests` and the debug harness:** SiRAT's `tests.list` / `tests.run` and the harness's test discovery and
   runs should become one set of methods in `tests`. Settle together with item 2.
