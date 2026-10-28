# SiRAT Station API: design, revision 2 (draft)

Revises the Oct 27, 2026 design document. Inputs: that document, `docs/API_REVIEW.md`, and the two frontend
proposals (`API_CHANGE_phy_and_prs.md`, `API_CHANGE_dut_connect_rpc_address.md`), which are folded in here.

The requirements were read for what the user needs to get done, not as a list of library calls to copy.
Where this design differs from how the original GUI worked, the reason is given.

Decisions taken on 2026-10-28 are recorded in section 11. One item is still open and marked **[open]**:
how read-sensitive registers are handled (section 12).

---

## Frontend status

The SiRAT frontend and its fake backend implement this revision for every feature that exists today:
`RpcAddress` on `dut.connect`, `dut.reconnect`, `dut.probe`, `WriteRes.verified`, `include_read_sensitive`,
`activity.abort`, instrument facts in `sys.status`, timeouts with `still_running` and `call.late`, and the
wire ops for `automation.seq.run` (`src/sirat_ui/core/wire_ops.py`). The Instruments page uses `rf.paths`,
`rf.connect`, `rf.disconnect`, `instruments.connect` and every `instruments.siggen/chamber/eca` method, with
chamber waits and ECA captures as instrument activities (`instrument_id`, `ActivityFinished.result`). Two
frontend choices to confirm: ECA pages carry int16 little-endian samples in mV, and a capture holds at most
1,000,000 samples per channel. The Advanced page uses `memory.read/write`, every `advanced.console`
method, `advanced.custom_function` (with the console's `session_id`, so the two share variables) and
`advanced.dut_control.describe/invoke`. Frontend choices to confirm: the GUI rejects a memory write that
crosses a 4-byte word; `ApiParam` leaves out the injected `dut` parameter; a console or function error
whose session has ended (`not_found` with `data.session_id`) makes the GUI open a new session and retry
once. Every method in this document now has a frontend user except the deferred `tests.*`.

## 1. What stays the same

- **Architecture.** Four layers: contracts, domain services, server, client SDK. The GUI imports only
  contracts and client. A CI check stops the GUI and contracts from importing NI drivers or pandas.
- **Transport and framing.** TCP on loopback, with the port from the workspace config (default 47800).
  Frames are a 4-byte big-endian length followed by a UTF-8 JSON body, 16 MB at most. Requests, replies and
  events share one connection.
- **State.** Facts per position plus `requires` on each method, all checked in one `check_requires`. The
  service enforces it; the GUI uses the same table to enable buttons.
- **Activities.** Only long operations are activities. They return an `activity_id` at once and report
  through `activity.*` events.
- **Conventions.** Pydantic v2, frozen models, unknown fields rejected, string enums, `domain.verb` names.
  Raw bytes are base64.
- **Testing plan and first slice.** Unchanged.

## 2. What changed, in short

| Area | Oct 27 draft | Revision 2 | Why |
|---|---|---|---|
| Timeouts | Service replies `timeout` and keeps going | `timeout` says `still_running`; a `call.late` event delivers the real outcome | After a timed-out write, the user needs to know whether it happened |
| Event `seq` | Per connection; a gap means refetch | Assigned when an event is *sent* | Dropped watch events must not look like missed events |
| Register tree | Names, address, width, ro/wo/rw | Plus descriptions, enum values, reset value, base address, six access types | The register view shows all of these, and the GUI can't parse the SVD itself |
| `registers.read` | `value, fields{}` | `value` | The GUI extracts fields from the tree; returning them twice adds nothing |
| Write verify | `verify_failed` error | `WriteRes.verified: bool` | The write *happened*. That's a warning for the user, not a failed call |
| Read-sensitive | Always refused by `read_many` / `watch` | Refused unless `include_read_sensitive=true`; single reads allowed | Keeps polling safe, but the user can still choose to read them |
| Memory | — | `memory.read`, `memory.write` | Memory viewer |
| Reconnect | Only a full `dut.connect` | `dut.reconnect` (RPC only) | Recovering after a firmware assert shouldn't redo the bench setup |
| Test connection | `dut.connect` then `dut.disconnect` | `dut.probe` | Testing must not drop a live connection |
| Connect target | Workspace config only | Optional `rpc` address | Hardware Configuration |
| PHY | `ble(name)` / `wifi(config_name)` | `lpw(name)` / `wifi(WifiPhyConfig)`; result has `function`, `overrides` | 802.15.4 loads like BLE; the WiFi form builds a full config |
| PRS | `rf.prs_route` | Plus `rf.prs_signals` | The signal list comes from a station-side module |
| Python | Stateless `py_exec` | Console sessions with a persistent namespace; mode `auto` | Variables survive between commands; eval with exec fallback |
| Custom functions | Looked up by name on the service | Code is sent with the call | The code lives in the user's file, which the service can't see |
| DUT control | `result_repr` | `result_text` (readable) + `result_json` when possible; error `cause` | Readable output and specific hints without matching message strings |
| Signal generator | `set(freq, level, role)`, `trigger(role)` | `get`, `set(SiggenConfig)`, `waveforms`, `trigger(mode)`, `rf(on)` | Load current config, pick a waveform, reload waveforms |
| Chamber | `set_temp(wait_stable)` | `read`, `set_temp`, `wait_stable` (activity) | Live temperature; waiting is optional and can be aborted |
| ECA | `capture(CaptureSpec)` | Plus `eca.sources` and `eca.result` (paged); `CaptureSpec` defined | The captured data has to come back |
| Tests | — | Not in v1 (deferred) | The Tests page is set aside for now (11.4) |
| Abort/status | `automation.seq.abort/status` | `activity.abort/status` | Every activity type aborts the same way |
| Activities | One per position, `pos` required | `pos` or `instrument_id` | Chamber waits and captures have no DUT position |
| Instrument tag | `instrument:<id>` and `instrument:rf_switch` mixed | `instrument:<kind>` | One form |
| `radio.*` | RX/TX configure/start/stop, RSSI, stats | Removed from v1 | Not in the requirements; PHY load plus DUT control covers RX/TX (11.2) |
| `automation.actions.list` | Actions "from the station" | Removed | Actions are the user's saved macros in the GUI (11.1) |
| `dut.reset` | Present | Removed | Nothing uses it; DUT control can reset |

---

## 3. Protocol

### Request, reply, event

```
request  { "id": 17, "method": "registers.read", "params": {...}, "timeout_ms": 5000 }
reply    { "id": 17, "ok": true,  "result": {...} }
         { "id": 17, "ok": false, "error": { "code": "wrong_state", "message": "...", "data": {...} } }
event    { "event": "registers.watch", "seq": 912, "data": {...} }
```

- Replies may arrive out of order; `id` matches them to requests.
- `seq` is per connection and goes up by one for every event *sent*. A gap means the connection lost
  events, so the client refetches `sys.status`. Watch events the server drops (keeping only the newest per
  subscription) never consume a `seq`.
- `timeout_ms` defaults to the RPC timeout setting (5 s, range 1–300 s).

### Timeouts

When a call runs past `timeout_ms`:

1. The service replies `timeout` with `data: { still_running: true }`.
2. The hardware call keeps running, and its position or instrument stays locked. Other calls for that
   position get `busy` with `data: { request_id }`.
3. When the call ends, the service sends `call.late { request_id, ok, result | error }`.

This tells the GUI whether a timed-out write actually happened.

### Activities

```
idle -> starting -> executing -> done
            \           |
             +----> aborting -> done
```

- An activity belongs to one position (`pos`) or one instrument (`instrument_id`). Each has at most one
  activity at a time.
- `activity.abort(activity_id)` is cooperative: it takes effect at the next wrapped hardware call and ends
  in the safe state.
- `activity.finished` is sent exactly once per activity, including after an abort or a service restart.
- If a hardware error happens during an activity on a position, the service sets that position's
  `fault`. `sys.recover` clears it.

## 4. State: facts and requires

### Facts

```python
class PositionFacts(Model):
    position: Position            # 1..4
    dut_connected: bool
    phy: str | None
    watching: bool
    rf_path: str | None           # rf.connect
    activity: ActivityState       # idle, starting, executing, aborting, done
    fault: Fault | None

class InstrumentFacts(Model):
    id: str                       # "siggen1", "switch1", "chamber1", "eca1"
    kind: InstrumentKind          # signal_generator, rf_switch, chamber, eca
    connected: bool
    model: str = ""               # what the instrument reports, e.g. "SMBV100B"
    activity: ActivityState

class StationStatus(Model):
    release_id: str
    positions: list[PositionFacts]
    instruments: list[InstrumentFacts]
    claim: str | None
```

`rx_configured` and `tx_configured` are removed together with `radio.*`.

### Tags

| Tag | Met when |
|---|---|
| `dut` | `dut_connected` |
| `phy` | `phy` is set |
| `idle` | `activity` is idle (the position's, or the addressed instrument's) |
| `no_fault` | `fault` is none |
| `instrument:<kind>` | Calls with an `id`: that instrument is connected. Calls without one: an instrument of that kind is connected |

`wrong_state.data.missing` always lists **tags**, never fact names.

### Reset rules

- A DUT disconnect clears `phy`, `watching` and `rf_path`, ends that position's watches, and closes
  console sessions bound to the position.
- Loading a PHY changes nothing else.
- An instrument drop ends that instrument's activity with `instrument_error`.

---

## 5. Common models

```python
Position = Annotated[int, Field(ge=1, le=4)]
class Empty(Model): pass
class ActivityRef(Model): activity_id: str
class Fault(Model): cause: str; detail: str; at: datetime
class RpcAddress(Model): host: NonEmptyStr; port: Annotated[int, Field(ge=1, le=65535)]
class ChipInfo(Model): part: str; revision: str; family: str
class ExecResult(Model):                       # console, custom functions
    stdout: str
    stderr: str
    result_text: str | None                    # None when the code had no value
    error: Traceback | None
class Traceback(Model): type: str; message: str; text: str
Access = Literal["ro", "wo", "rw", "w1", "rw1", "unknown"]   # SVD read-only, write-only, read-write,
                                                             # writeOnce, read-writeOnce, anything else
```

---

## 6. Methods

Each entry lists the method, its input and output, and what it requires. `pos` is a `Position`.

### sys

| Method | Result | Requires |
|---|---|---|
| `sys.hello(client, protocol)` | `release_id, protocol, server_time` | — |
| `sys.describe()` | `methods[]: name, req_schema, res_schema, requires` | — |
| `sys.status()` | `StationStatus` | — |
| `sys.subscribe(topics[])` | `Empty`. Topics: `status, activity, watch, instrument, log` | — |
| `sys.recover(pos)` | `Empty`. Applies the safe state and clears the fault | — |

### dut

| Method | Result | Requires |
|---|---|---|
| `dut.connect(pos, config_type: EFX\|EFR32, config_file?: str, rpc?: RpcAddress)` | `ConnectRes: chip: ChipInfo, rpc: RpcAddress` | `no_fault` |
| `dut.reconnect(pos)` | `Empty`. RPC only (`rpc_io.Connect()`); `not_found` if the position was never connected | `no_fault` |
| `dut.disconnect(pos)` | `Empty` | — |
| `dut.probe(pos, rpc?: RpcAddress, timeout_s)` | `ProbeRes: ok, latency_ms, detail`. Never connects or disconnects; `rpc` omitted probes the workspace address for `pos` | — |
| `dut.info(pos)` | `DutInfo: chip, revision, hw{}, rta{host, port, timeout_s}, app{name, version, build_time}?` | `dut` |
| `dut.load_phy(pos, phy: PhySpec)` | `LoadPhyRes: name, function, overrides: [[key, value]]` | `dut, idle` |
| `dut.set_rpc_timeout(seconds 1..300)` | `Empty`. Station-wide: every DUT, and the default `timeout_ms` | — |

- `rpc` omitted means the workspace config.
- `dut.connect` sends `log.line` events with `source="dut.connect"` and `pos` while it runs, so the
  connect sheet can show progress.

```python
PhySpec = LpwPhy | WifiPhy                     # tagged by "kind"
class LpwPhy(Model):  kind: Literal["lpw"];  name: str          # BLE_1M, IEEE802154_2p4G, ...
class WifiPhy(Model): kind: Literal["wifi"]; config: WifiPhyConfig
class WifiPhyConfig(Model):
    mode: Literal["RX", "TX"]
    standard: Literal["802.11b", "802.11g", "802.11a", "802.11n", "802.11ac", "802.11ax", "802.11be"]
    channel: int                               # must belong to the standard's band
    power_mode: Literal["HP", "LP", "MP"]      # MP only for ax/be
    rate: str
    phy_name: str
    tx_params: WifiTx | None                   # pkt_length 1..65535, num_pkts 0..1e6, transmit_mode, aggr_enable
    advanced: WifiAdvanced | None              # ppdu_type, gi_ltf, dcm 0|1, bandwidth
```

`wifi` on a non-Everest DUT fails with `invalid_params`.

### registers

| Method | Result | Requires |
|---|---|---|
| `registers.tree(pos)` | `RegisterTree` | `dut` |
| `registers.read(pos, name)` | `value` | `dut` |
| `registers.read_many(pos, names[], include_read_sensitive=false)` | `items[]: name, value \| error` | `dut` |
| `registers.write(pos, name, value, confirm=false, verify=true)` | `WriteRes` | `dut, idle` |
| `registers.write_field(pos, name, field, value, confirm=false, verify=true)` | `WriteRes` | `dut, idle` |
| `registers.watch(pos, names[], interval_s 0.1..60, include_read_sensitive=false)` | `sub_id` | `dut` |
| `registers.unwatch(sub_id)` | `Empty` | — |

```python
class RegisterTree(Model):
    tree_id: str                               # content hash; the GUI caches by (chip, revision, tree_id)
    peripherals: list[PeripheralInfo]
class PeripheralInfo(Model):
    name: str; base_address: int; description: str
    critical: bool                             # writes need confirm=true (CMU, EMU, MSC, SMU)
    read_sensitive: bool                       # reading has side effects (USART, I2C, SPI)
    registers: list[RegisterInfo]
class RegisterInfo(Model):
    name: str; address: int; width: int; access: Access; reset_value: int | None; description: str
    fields: list[FieldInfo]
class FieldInfo(Model):
    name: str; lsb: int; width: int; access: Access; description: str
    enums: list[EnumValue]
class EnumValue(Model): name: str; value: int; description: str
class WriteRes(Model): value_written: int; value_readback: int | None; verified: bool
```

- Writes: `confirmation_required` if `critical` and not `confirm`. `access_denied` if the target isn't
  writable (`ro`, `unknown`). `out_of_range` if the value doesn't fit the field.
- Reads: `access_denied` for `wo`, `w1` and `unknown`.
- `verified` is false when the read-back differs. That's not an error; the GUI warns and shows the
  read-back value. `value_readback` is None when the register can't be read back.
- Read-sensitive registers: a single `registers.read` is allowed, because the user asked for exactly that
  register. `read_many` and `watch` return `read_sensitive` for them unless the caller opts in
  **[open]**: this rule is a placeholder until section 12 is settled.
- If `tree` is ever bigger than one frame, it moves to the paging pattern in 6.9.

### memory (new)

| Method | Result | Requires |
|---|---|---|
| `memory.read(pos, address, size 1..4096)` | `MemoryBlock: address, data (base64)` | `dut` |
| `memory.write(pos, address, value, size: 1\|2\|4)` | `MemoryWriteRes: address, value_written, value_readback` | `dut, idle` |

- `read` aligns the start down to 4 bytes and the length up, and returns the aligned `address` it actually
  read. The GUI formats bytes, words or dwords, little-endian.
- `write` does a read-modify-write of the aligned 4-byte word under the position lock, so an unaligned
  write is atomic with respect to other calls. The GUI asks the user to confirm every memory write.

### rf

| Method | Result | Requires |
|---|---|---|
| `rf.paths()` | `names[]` (from the switch configuration) | `instrument:rf_switch` |
| `rf.connect(pos, path)` | `Empty`; sets `rf_path` | `instrument:rf_switch` |
| `rf.disconnect(pos)` | `Empty` | `instrument:rf_switch` |
| `rf.prs_signals(pos)` | `PrsSignalCatalog: family, module, signals[]` | `dut` |
| `rf.prs_route(pos, PrsRoute)` | `Empty` | `dut` |

- The current path is the `rf_path` fact, so there's no `rf.current`.
- `PrsRoute` is `{signal, pin: PA0..PD7, channel: 0..11}`. `signal="DISABLE"` removes a route.
  `invalid_params` for port A/B with channels 6–11, or port C/D with 0–5.

### instruments

| Method | Result | Requires |
|---|---|---|
| `instruments.list()` | `InstrumentFacts[]` | — |
| `instruments.connect(id, address?)` | `Empty` | — |
| `instruments.disconnect(id)` | `Empty` | — |
| `instruments.siggen.get(id)` | `SiggenConfig` (what the instrument has now) | `instrument:signal_generator` |
| `instruments.siggen.set(id, SiggenConfig)` | `Empty` | `instrument:signal_generator, idle` |
| `instruments.siggen.waveforms(id, reload=false)` | `names[]`; `reload` rescans the waveform files | `instrument:signal_generator` |
| `instruments.siggen.trigger(id, mode: infinite\|single)` | `Empty` | `instrument:signal_generator` |
| `instruments.siggen.rf(id, on: bool)` | `Empty` | `instrument:signal_generator` |
| `instruments.chamber.read(id)` | `ChamberReading: actual_c, target_c, stable` | `instrument:chamber` |
| `instruments.chamber.set_temp(id, celsius)` | `Empty`; returns when the setpoint is accepted | `instrument:chamber, idle` |
| `instruments.chamber.wait_stable(id, tolerance_c=0.5, hold_s=60, timeout_s=3600)` | `ActivityRef` | `instrument:chamber, idle` |
| `instruments.eca.sources(id)` | `EcaSources: channels[], triggers[]` | `instrument:eca` |
| `instruments.eca.capture(id, CaptureSpec)` | `ActivityRef`; `finished.result` is `{capture_id}` | `instrument:eca, idle` |
| `instruments.eca.result(capture_id, offset=0, count=65536)` | `CapturePage` | — |

```python
class SiggenConfig(Model):
    sg_type: str = "PacketSrw"
    input_config_name: str                     # one of siggen.waveforms
    frequency_hz: float                        # the GUI shows MHz
    power_dbm: Annotated[float, Field(ge=-150, le=30)]
    overrides: dict[str, JsonValue] = {}

class CaptureSpec(Model):
    channels: list[str]                        # from eca.sources
    trigger: str                               # a trigger source, or "immediate"
    edge: Literal["rising", "falling", "either"] = "rising"
    sample_rate_hz: float
    duration_s: float
    pretrigger_pct: Annotated[int, Field(ge=0, le=90)] = 10

class CapturePage(Model):
    meta: CaptureMeta                          # spec, started_at, sample_count, chip, pos
    offset: int; count: int
    channels: dict[str, str]                   # channel -> base64 little-endian samples for this page
    more: bool
```

- The chamber's live display polls `chamber.read` at the interval the user picks. "Wait for stable" is an
  activity, so it shows progress and can be aborted.
- Captures are kept on the service until `eca.result` has read the last page, or for 1 hour.
- Saving a capture to CSV or binary happens in the GUI.

### automation

| Method | Result | Requires |
|---|---|---|
| `automation.seq.run(pos, ops: list[Op], stop_on_error=true)` | `ActivityRef` | `dut, idle, no_fault` |

```python
Op = (RegisterWriteOp | FieldWriteOp | CustomFunctionOp | RfSwitchOp | SignalGeneratorOp | LoadPhyOp
      | LoadWifiPhyOp | DutControlMethodOp | DutReconnectOp | PrsRouteOp | GfskPacketOp)   # tagged by "type"
# every op may carry group: str (the action it came from); activity.progress echoes it
class CustomFunctionOp(Model):   type: Literal["custom_function"]; function_name: str; code: str
class SignalGeneratorOp(Model):  type: Literal["signal_generator"]; instrument_id: str; config: SiggenConfig
class RfSwitchOp(Model):         type: Literal["rf_switch"]; path: str
class GfskPacketOp(Model):       type: Literal["gfsk_packet"]; code: str
...                              # the others follow src/sirat_ui/stores/schemas/operations.py
```

- The client builds `ops[]` from the user's actions and sequences. It expands a sequence into its actions'
  ops, each tagged with `group`, and copies custom-function code in from the user's file.
- A `sequence` op never goes on the wire.
- The GUI's files may hold extra keys; the client sends only the wire model's fields.
- Ops in one run share one Python namespace, so a custom function can use a variable set by an earlier one.
- `RfSwitchOp` uses the run's `pos`, so it no longer carries `dut_position`.

### activity

| Method | Result |
|---|---|
| `activity.abort(activity_id)` | `Empty` |
| `activity.status(activity_id)` | `state, step, total, results[]` |

### advanced

| Method | Result | Requires |
|---|---|---|
| `advanced.console.open(pos)` | `session_id` | `dut` |
| `advanced.console.exec(session_id, code, mode: auto\|eval\|exec = auto)` | `ExecResult` | `dut` |
| `advanced.console.names(session_id)` | `names[]: name, type, doc` | — |
| `advanced.console.close(session_id)` | `Empty` | — |
| `advanced.custom_function(pos, name, code, session_id?)` | `ExecResult` | `dut, idle` |
| `advanced.dut_control.describe(pos)` | `ApiTree` | `dut` |
| `advanced.dut_control.invoke(pos, path, args[], kwargs{})` | `InvokeRes` | `dut, idle` |

**Console sessions**

- A session's namespace persists until it's closed, the client disconnects, or the DUT disconnects. It
  holds `dut`, the test utilities and, in debug mode, `self`.
- `auto` tries `eval` and falls back to `exec` on `SyntaxError`.
- Command history is GUI-only.

**Custom functions**

- The code runs wrapped in a function, so a top-level `return` works.
- With a `session_id`, the call uses that session's namespace and stores `result_<name>` and
  `last_dut_api_result` there. Without one, it gets a fresh namespace.

**DUT control**

```python
class ApiTree(Model): packages: list[ApiPackage]           # Common, Host, LPW, WiFi
class ApiPackage(Model): name: str; modules: list[ApiModule]
class ApiModule(Model): name: str; path: str; methods: list[ApiMethod]
class ApiMethod(Model): name: str; path: str; signature: str; doc: str; params: list[ApiParam]
class ApiParam(Model): name: str; annotation: str; default_repr: str | None; required: bool
class InvokeRes(Model): result_text: str; result_json: JsonValue | None; result_type: str
```

- Classes are preferred over modules and private methods are skipped, so the GUI shows the tree as it
  comes.
- `dut` is injected when the method takes it.
- `result_text` is formatted for reading: a list or tuple shows its length and first 10 items, a dict shows
  all pairs, and an object shows its type and public attributes.
- On failure the error is `hardware_error`, with
  `data.cause: rpc_timeout | rpc_transport | rail_assert | other` and a traceback. The GUI words the hint
  for each cause.

### tests (deferred, not in v1)

The Tests page (req 33) is set aside for now (11.4). When it comes back, the sketch was `tests.list()` and
`tests.run(pos, ids[]) -> ActivityRef` with per-test results in `activity.finished`, and the first question
is where the list of tests comes from.

---

## 7. Events

| Event | Data | When |
|---|---|---|
| `status.changed` | `StationStatus` | Any fact changes |
| `activity.progress` | `activity_id, pos?, instrument_id?, step, total, message, group?` | |
| `activity.finished` | `activity_id, pos?, instrument_id?, ok, results[], result?, error?` | Exactly once |
| `registers.watch` | `sub_id, pos, ts, values[{name, value}]` | Once per interval; only the newest is kept if the client is slow |
| `dut.disconnected` | `pos, cause, detected_by` | After the 2 s debounce |
| `instrument.changed` | `InstrumentFacts` | |
| `call.late` | `request_id, ok, result \| error` | A timed-out call finished |
| `log.line` | `ts, level, source, text, pos?` | |

## 8. Errors

One shared set of codes. Domains add detail in `data`.

| Code | Meaning |
|---|---|
| `wrong_state` | Requires unmet; `data.missing` lists tags |
| `invalid_params` | Schema or range validation failed |
| `unknown_method` | Not in `sys.describe` |
| `timeout` | Call exceeded `timeout_ms`; `data.still_running` |
| `busy` | Position or instrument locked; `data.request_id` |
| `claimed` | Another owner holds the station |
| `confirmation_required` | Critical register written without `confirm` |
| `read_sensitive` | Read-sensitive register in `read_many` / `watch` without opt-in |
| `access_denied` | Register or field isn't readable / writable |
| `out_of_range` | Value doesn't fit |
| `not_found` | Register, path, id, session or capture unknown |
| `dut_disconnected` | Link lost during the call |
| `instrument_error` | Instrument reported an error |
| `hardware_error` | Library raised; sets `fault` during an activity; `data.cause` where known |
| `aborted` | Activity aborted |
| `internal` | Bug; includes a trace id |

`verify_failed` is gone: see `WriteRes.verified`.

Library exceptions are mapped to these codes at the domain-service boundary. `hardware_error` and
`dut_disconnected` update the facts *before* the reply, so the next `sys.status` is already right.

## 9. Feature mapping

| Feature | API | GUI only |
|---|---|---|
| Connect, reconnect, disconnect, recovery dialog | `dut.connect/reconnect/disconnect`, `dut.disconnected` | Debounce of repeated dialogs |
| Hardware configuration, test connection | `dut.probe`, `dut.set_rpc_timeout` | The settings file |
| System information | `dut.info` | Copy All |
| Register tree, detail, read, write, confirm, verify | `registers.*` | Search, favorites, notes, formulas, history, display format |
| Dumps, Read All, Radio Calculator diff | `registers.read_many` | CSV files, comparison, `.cfg` parsing |
| Watch list, data logger | `registers.watch` | Field extraction, plots, CSV export |
| Memory viewer | `memory.read/write` | Hex dump formatting, last address |
| PHY loading | `dut.load_phy` | Forms, packet visualizer |
| PRS routing | `rf.prs_signals`, `rf.prs_route` | Port/channel check before sending |
| RF switch | `rf.paths`, `rf.connect`, `instruments.list` | — |
| Signal generator | `instruments.siggen.*` | Its settings file, generated code |
| BLE packet, GFSK packet | — | Code generation only |
| Chamber | `instruments.chamber.*` | Polling interval |
| ECA capture | `instruments.eca.*` | Plot, markers, measurements, file export |
| Actions, sequences | `automation.seq.run`, `activity.*` | The action and sequence files, editing, code generation |
| Custom functions | `advanced.custom_function` | The functions file, editor |
| Python console | `advanced.console.*` | History, colors |
| DUT control explorer | `advanced.dut_control.*` | Parameter parsing from text |
| Test execution | Deferred (not in v1) | — |
| Sessions, settings import/export, logs | — | All |

## 10. Open questions carried over

1. **Debug mode attach.** Is there a `dut.attach(pos)` so SiRAT uses the `dut` a paused test already
   connected? Or does the test hand it to the service?
2. **pandas and NI drivers in one process.** The service startup check decides.
3. **One service or several per station.** Affects `sys.hello` and `claim`.
4. **Auth.** Loopback with no auth. Is that enough, given `advanced.console` runs arbitrary code on a
   shared station?
5. **dut_control argument types.** JSON only, or do some methods need typed objects?

## 11. Decisions (2026-10-28)

The requirements were written from a demo a validation engineer built, so they're read for what users need
to get done, not as a spec to copy.

1. **Actions belong to the GUI.** Decided. `automation.actions.list` is removed. Actions and sequences are
   each user's saved macros, kept in their own files and edited in SiRAT; the service only *runs* the ops
   it's given. If something other than SiRAT (a test, or the hub later) ever needs to run actions by name,
   a station-side library can be added then, as its own domain.
2. **`radio.*` is not in v1.** Decided. The requirements have no RX/TX setup screen: "RX or TX" only
   appears as the mode inside the WiFi PHY form (req 23, sent with `dut.load_phy`), and RSSI only appears
   in a custom-function example (req 15). The `rx_configured` / `tx_configured` facts and the
   `radio_rx` / `radio_tx` tags go with it. Add them back when a screen needs them.
3. **Read-sensitive registers.** Not decided; deferred to a later discussion. See section 12.
4. **The Tests page is out of v1.** Decided. `tests.*` is removed for now; req 33 is set aside, and the
   frontend's Tests nav entry stays a "planned" placeholder.

## 12. Open items (come back to these)

1. **Read-sensitive registers (USART, I2C, SPI).** Reading them has side effects, such as emptying a
   receive buffer. Options:
   - a single explicit read is allowed, and bulk reads (dumps, Read All) and watches need
     `include_read_sensitive=true` (the current placeholder in 6, and what the frontend does today: dumps
     and Read All skip them);
   - bulk reads and watches always refuse them (the Oct 27 draft);
   - never refuse, only log a note (the original GUI).

   Raised 2026-10-28; to be discussed with the validation engineers.
