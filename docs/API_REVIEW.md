# Review: SiRAT Station API Design Document (Oct 27, 2026) against sirat_requirements.txt

Reviewed by the frontend, section by section against req 1–35. "Req N" means sirat_requirements.txt §N.

## Verdict

The architecture is sound: the four layers, facts + requires instead of a session state machine, one typed
contracts package, events for watch/progress/disconnect, and a fake per domain. Keep all of that.

The method list is less accurate. Seven features with hardware behind them have no API, or only part of
one. Four places contradict the requirements. A few things in the doc don't agree with each other. None of
this needs a redesign; it's mostly missing methods and missing model definitions.

Four gaps already have frontend proposals, which the fake backend implements:
- `docs/API_CHANGE_phy_and_prs.md`: WiFi PHY config, `LoadPhyRes.function`/`overrides`, `rf.prs_signals`.
- `docs/API_CHANGE_dut_connect_rpc_address.md`: per-connection RPC host/port.

They're listed below for completeness but not repeated in detail.

---

## 1. Features with no API (blocking for that feature)

| Req | Feature | What's missing | Suggested method |
|---|---|---|---|
| 19 | Memory viewer | Nothing reads or writes raw memory (`dut.rpc_io.ReadByteBlock`). | `memory.read(pos, address, size 1..4096) -> bytes (base64)`, requires `dut`. `memory.write(pos, address, value, size: byte\|word\|dword) -> Empty`, requires `dut, idle`. The service does the 4-byte aligned read-modify-write under the position lock, so it's atomic. |
| 3 | Reconnect RPC | The recovery dialog and the `dut_reconnect` op call `dut.rpc_io.Connect()` only. The only API option is a full `dut.connect`, which re-runs `BenchUtils.connect_six_dut_rf`. | `dut.reconnect(pos) -> Empty`. It needs the position to have been connected before, not `dut`. |
| 3 | Connection progress | Req 3 wants "connection progress in real-time" in the console. `dut.connect` is a single reply. | Send `log.line` events with `source="dut.connect"` and `pos` while it runs. Or say plainly that it's a reply only. |
| 20 | Python console | (1) The namespace persists for the whole console session, but `py_exec` is stateless. (2) Req 20 tries `eval` first and falls back to `exec` on `SyntaxError`; the API makes the client pick `mode`. (3) Help lists the namespace, and nothing returns it. | `advanced.py_session_open(pos) -> session_id`, `py_session_close(session_id)`, and `py_exec(session_id, code, mode: auto\|eval\|exec)`, with `auto` as the default. `py_namespace(session_id) -> names[]: name, type`. |
| 15 | Custom functions | Function code lives in the GUI's `~/.sirat_custom_functions.json`, so the service can't look up `custom_function(pos, name, args)` by name. Req 15 also wants a namespace shared between calls, and `result_<name>` / `last_dut_api_result` stored there. Req 15's own example has a top-level `return`, so the service has to wrap the code in a function. | `advanced.custom_function(pos, name, code, session_id?)`. The `custom_function` op carries `code` too. The GUI fills it in from the file when it builds `ops[]`. |
| 33 | Test execution | No `tests` domain, and the feature mapping doesn't list it. | `tests.list() -> TestInfo[]` and `tests.run(pos, names[]) -> ActivityRef`. Progress comes through `activity.progress`, and per-test `{name, ok, duration_s, output}` in `activity.finished.results`. Abort through `automation.seq.abort`, or a shared `activity.abort`. |
| 25 | Signal generator | `siggen.set(id, freq_hz, level_dbm, role)` has no `sg_type`, `input_config_name` or `overrides`. Nothing reads the current config ("Load from SG Role"), lists waveforms (the InputConfigName drop-down) or reloads them ("Reload Waveform"). The `signal_generator` op doesn't say which instrument. | `siggen.set(id, SiggenConfig{sg_type, input_config_name, frequency_hz, power_dbm, overrides})`, `siggen.get(id) -> SiggenConfig`, `siggen.waveforms(id, reload=false) -> names[]`, and `siggen.rf(id, on: bool)`. Rename the trigger argument (see 3.3). |
| 29 | Chamber | Nothing reads the current temperature. Req 29 wants a live display showing target vs actual. | `chamber.read(id) -> {actual_c, target_c, stable}`, polled by the GUI at the configurable interval. Or an `instrument.changed` payload that carries readings. |
| 30 | ECA capture | `CaptureSpec` isn't defined, and there's no way to get the captured data back. The doc says captures use "a paged method", but none is defined. | Define `CaptureSpec` (trigger source and edge, sample rate, duration, pre-trigger, channels). `activity.finished.result` returns `capture_id`. Add `eca.result(capture_id, page) -> {meta, channels[], samples (base64)}`. |
| 23 | WiFi PHY | `PhySpec.wifi(config_name)` can only name a stored config; req 23 builds a full one. | Proposed in API_CHANGE_phy_and_prs.md. Also, `ble(name)` should be `lpw(name)`, because req 23 loads 802.15.4 PHYs the same way. |
| 24 | PRS signals | No call lists the family's PRS signals. | Proposed in API_CHANGE_phy_and_prs.md. |
| 32 | Hardware config | `dut.connect` can't take the RPC host/port from Hardware Configuration. | Proposed in API_CHANGE_dut_connect_rpc_address.md. |
| 31 | System info | `DutInfo` has `hw{}` and `rta{}`, but req 31 also shows firmware name, version and build time. | `DutInfo.app{}`, optional. The fake already returns it. |

## 2. Contradictions with the requirements

1. **Access types.** The API has `Access: ro, wo, rw`. Req 7 has six: `read-only`, `write-only`,
   `read-write`, `writeOnce`, `read-writeOnce` and `unknown`. Each has its own permission rule (`W1` can't be
   read, unknown can be neither read nor written) and its own color and badge. Extend the enum to six values.
2. **Read-sensitive peripherals.** The API *refuses* USART/I2C/SPI in `read_many` and `watch`
   (`read_sensitive`). Req 7 says "No blocking, just informational logging". Refusing may be the safer
   choice, but it's a behavior change, so record it as a decision. Today the GUI's dumps and Read All skip
   these peripherals to match the API.
3. **Actions come from the GUI, not the station.** The doc says `automation.actions.list() -> Action[] (from
   the station)`. Req 13 keeps actions in `~/.sirat_actions.json` on the client, and the GUI sends their ops
   through `automation.seq.run`. Remove `actions.list`, or say what station-side actions are and how they
   relate to the user's file.
4. **Register metadata.** `RegisterInfo` and `FieldInfo` have no descriptions, enum values or reset values,
   and peripherals have no base address or description. Req 5 shows field descriptions, enum names and
   enum tooltips. The doc also lists "SVD parsing and search" as GUI-only. But req 4 builds the tree from
   `SvdLoader.load_peripherals(dut.rm)` on the station, and the GUI has no SVD file. So `registers.tree` has
   to carry descriptions, enums (`name, value, description`) and the reset value. Parsing stays in the
   service; only *search* is GUI-only.
5. **Open question 5 is already answered.** "Are the chamber and ECA driven from SiRAT screens?" Yes: req 29
   and req 30 both specify their own dialogs. Close the question.

## 3. Inconsistencies inside the doc

1. **Missing-tag names.** The `wrong_state` example shows `"missing": ["dut_connected"]` (a fact name), but
   the requires table uses tags (`dut`). Use tags everywhere; the GUI maps them to text.
2. **Instrument tag.** Tags are defined as `instrument:<id>`, but `rf.connect` requires
   `instrument:rf_switch`, which is a *kind*. Pick one form. `instrument:<kind>` works for methods with no
   id argument; `instrument:<id>` works when the id is a parameter.
3. **"role" means two things.** In `siggen.set(..., role)` it means the Gen1Role instrument role, the way
   req 25 uses the word. In `siggen.trigger(id, role)` it means a *trigger kind*
   (`InfiniteTrigger | SingleTrigger | RfOn | RfOff`). Rename the second to `trigger(id, kind)` and move
   RF on/off to its own method.
4. **Activities and positions.** "One activity per position at a time", and `activity.*` events carry
   `pos`. `chamber.set_temp(wait_stable)` and `eca.capture` are activities with no position. Make `pos`
   optional and add `instrument_id`, or say which position an instrument activity belongs to.
5. **Undefined models.** These are named but never defined: `RxConfig`, `TxConfig`, `CaptureSpec`, `Op`
   (the 12 variants), `Action`, `LoadPhyRes`, the `DutInfo` fields, `SiggenConfig`, the paged-result shape,
   and `dut.connect`'s `config_type` enum (req 3: `EFX | EFR32`). The GUI's op schemas in
   `src/sirat_ui/stores/schemas/operations.py` follow req 13 and could be the starting point for `Op`.
6. **RPC timeout scope.** `dut.set_rpc_timeout(seconds)` has no position, but `dut.info.rta.timeout_s` is
   per DUT. Say whether it's station-wide or per position.

## 4. Protocol details worth settling before building

1. **Event `seq` vs dropped watch events.** A gap in `seq` means "refetch with `sys.status`", and the
   server may drop older `registers.watch` events. If `seq` is assigned before the drop, every drop looks
   like a gap. Assign `seq` when an event is *sent*, not when it's produced.
2. **What a timeout leaves behind.** On `timeout`, the hardware call keeps running. Two things follow:
   - Later calls on that position wait on the lock. Do they get `busy`, or queue?
   - For a write, the GUI can't tell whether it happened.

   Suggest: `timeout.data.still_running: true`, then a `status.changed` event (or a new `call.finished`
   event) when it ends.
3. **`verify_failed` is an error, but the write happened.** Req 7 treats this as a warning: the write
   happened and the read-back value is shown. As an error, every client has to remember that this one error
   means the write succeeded. Return it in the result instead:
   `WriteRes{value_written, value_readback, verified: bool}`.
4. **Unknown fields rejected vs files that keep them.** The wire rejects unknown fields. The GUI keeps
   unknown keys in its action files so files written by older or newer versions still load and save
   correctly. The client must therefore reduce each op to its wire model before `seq.run`. Note this in the
   contract.
5. **Sequence progress loses action boundaries.** `ops[]` is flat, and req 14 highlights *the action* that's
   running. Add an optional `group` (the action name) to each op and echo it in `activity.progress`.
6. **Test Connection side effect.** Req 32's "Test Connection … does not persist connection". With only
   `dut.connect`/`disconnect`, testing a position that's already connected drops the user's live
   connection. A `dut.probe(pos, rpc_host, rpc_port, timeout_s)` that doesn't keep the connection would
   avoid that.

## 5. In the API, but not backed by any requirement

- **`radio.*`** (configure/start/stop RX and TX, RSSI, packet stats). No req section describes RX/TX setup;
  RSSI only appears inside a custom-function example. Either a requirement is missing, or this domain is
  scope creep for SiRAT. The feature mapping still lists "Rx and Tx setup and run: radio.*".
- **`dut.reset`**: harmless, but no req calls it.
- **`InstrumentKind.spectrum_analyzer`, `power_supply`**: no SiRAT screen uses them.

Confirm where these came from before building them.

## 6. Frontend impact (this repo)

- **The `custom_function` op.** The frontend sends `{type, function_name}` only, which the real service
  can't run (§1, req 15). Once the API takes `code`, `ActionService` should inline the code from
  `~/.sirat_custom_functions.json` when it builds `ops[]`.
- **`verify_failed`** is handled as an error carrying `written`/`readback`. That's fine today; it's a small
  change if 4.3 is adopted.
- **The fake already implements the four proposals above.** Everything else in §1 is unbuilt on both sides:
  memory viewer, reconnect, console sessions, tests, siggen get/waveforms, chamber read and ECA results.

## Suggested next steps

1. Decide 2.2 (read-sensitive) and §5 (the `radio.*` scope). Those are product decisions, not API detail.
2. Add the §1 methods and the §3.5 models to the doc. Fold in the two API_CHANGE docs.
3. Fix the §3 inconsistencies and settle §4.1–4.3. They're cheap now and expensive once both sides ship.
