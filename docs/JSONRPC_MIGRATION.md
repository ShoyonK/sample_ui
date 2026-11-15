# Plan: JSON-RPC 2.0 and a real station gateway

> **The current contract is [STATION_API.md](STATION_API.md)** (protocol 2), with its generated [reference](STATION_API_REFERENCE.md). This file is the record of the migration to JSON-RPC 2.0; its wire-shape notes (section 1) and open items (section 7) are out of date.

**Status: done**, including the hardening in section 9 and pydantic validation in section 10. Tests: 667
passed, 1 xfailed (92 wire unit tests, 32 contract tests over TCP, 1 end-to-end run of the app over TCP); chaos
50 passed; pyrefly 0 errors. Still
open: agreement from the station team on the protocol and the field names (section 7).

Differences from the plan as written:
- `QtPoster` uses Qt's default connection, which already queues a signal emitted on another thread; the
  explicit queued connection type isn't in PyQt5's stubs.
- `CallLate.request_id` is now `int | str`, since JSON-RPC ids may be strings.
- With `--backend api`, the app doesn't auto-connect a DUT at start and doesn't seed demo data into the home
  folder.
- Section 5's "reconnecting is left for later" is done: see section 9.

Two changes, done together:

1. The Station API's messages move to **JSON-RPC 2.0**. Framing and transport stay as they are.
2. The app gets **`ApiStationGateway`**, a client that speaks that protocol over TCP. The fake station gets a TCP
   front end (`FakeStationServer`) so the client can be built and tested before the real station service
   exists.

Nothing above the gateway changes. Services and ViewModels keep using the interfaces in `gateway/port.py`
(`Call`, `ApiError`, the models in `models/`), so they can't tell which backend they're on.

## 1. The protocol

### Framing (unchanged)

TCP on loopback, port from the workspace config (default 47800). Each message is a 4-byte big-endian length
followed by a UTF-8 JSON body of at most 16 MB. Requests, replies and events share one connection.

### Envelope

```
request       {"jsonrpc": "2.0", "id": 17, "method": "registers.read",
               "params": {"pos": 1, "name": "CMU.CLKEN0", "_meta": {"timeout_ms": 5000}}}
reply         {"jsonrpc": "2.0", "id": 17, "result": 3}
error reply   {"jsonrpc": "2.0", "id": 17,
               "error": {"code": -32001, "message": "DUT 1 isn't ready", "data": {"reason": "wrong_state",
                                                                                   "missing": ["dut"]}}}
event         {"jsonrpc": "2.0", "method": "registers.watch", "params": {"seq": 912, "data": {...}}}
```

- `params` is always an object (named parameters), never an array.
- `_meta` is a reserved key in `params` for call options. Today it holds `timeout_ms` (defaults to the RPC
  timeout setting). The leading underscore keeps it apart from method parameters.
- A reply has `result` or `error`, never both. The old `ok` flag is gone.
- Events are JSON-RPC **notifications**: no `id`, the event name as `method`. `params.seq` keeps its meaning
  (per connection, +1 per event sent; a gap means refetch `sys.status`); `params.data` is the event's data.
- Batches (a JSON array of requests) aren't supported; the server answers one `-32600` error.
- A request without an `id` (a client notification) is run and gets no reply. The client never sends one.

### Error codes

JSON-RPC needs an integer `code`. The string code travels as `data.reason`, so nothing that reads errors by
name changes. The client maps back to `ErrorCode` by `data.reason` first, then by `code`.

| `code` | `data.reason` | Notes |
|---|---|---|
| -32700 | `invalid_params` | Parse error (the frame isn't JSON) |
| -32600 | `invalid_params` | Invalid request (not a JSON-RPC request object, or a batch) |
| -32601 | `unknown_method` | Method not found |
| -32602 | `invalid_params` | Invalid params |
| -32603 | `internal` | Internal error |
| -32001 | `wrong_state` | `data.missing` lists tags |
| -32002 | `timeout` | `data.still_running`, `data.request_id` |
| -32003 | `busy` | `data.request_id` |
| -32004 | `claimed` | |
| -32005 | `confirmation_required` | |
| -32006 | `read_sensitive` | |
| -32007 | `access_denied` | |
| -32008 | `out_of_range` | |
| -32009 | `not_found` | |
| -32010 | `dut_disconnected` | |
| -32011 | `instrument_error` | |
| -32012 | `hardware_error` | `data.cause` |
| -32013 | `aborted` | |

-32000 to -32099 is the range JSON-RPC sets aside for server-defined errors.

### Timeouts and late results

Unchanged in meaning. A timed-out call is answered with `-32002` and `data: {still_running: true,
request_id}`, where `request_id` is the **JSON-RPC `id`** of the call that timed out. When it finishes, the
`call.late` event carries that same `request_id`.

The client also keeps its own deadline (`timeout_ms` plus a 2 s grace). If no reply arrives by then, the call
fails with `timeout` and `data: {still_running: null, client_side: true}`: the client can't tell whether the
station is still working on it.

### Wire shapes

Parameter names follow `docs/API_DESIGN.md` (`pos`, `id`, `names`...). Results and events are the frontend's
models (`models/`) encoded field by field, with these rules:

- dataclass → object with the same field names, except `position` → `pos` in events (as the doc writes them);
- tuple and list → array; enum → its value; `None` → `null`;
- `PhySpec` is tagged by `kind` (`lpw` / `wifi`);
- `ApiError` inside a result (`read_many` items, `activity.finished.error`) → `{code, message, data}` like an
  error reply;
- where the doc names a wrapper object the result is wrapped: `registers.tree` → `{tree_id, peripherals}`,
  calls that start an activity → `{activity_id}` (`ActivityRef`);
- `registers.watch` events carry `values` as `[{name, value}]`, as the doc says.

Where the doc's model and the frontend's differ in a field (for example the register tree's `reset_value`
vs the frontend's `reset`), the wire follows the frontend for now. Section 7 lists these for agreement with
the station team.

## 2. Module layout

```
gateway/
  wire/
    framing.py        read and write length-prefixed frames; the 16 MB limit
    jsonrpc.py        the envelope: build and check requests, replies, errors, notifications; the code table
    codec.py          models ↔ JSON (dataclasses by type hints, the rules above)
    methods.py        the method table: wire name, gateway attribute, parameters, result type, wrapper
    events.py         the event table: GatewayEvent type ↔ notification name
  api/
    client.py         ApiStationGateway (implements StationGateway)
    connection.py     the socket, its reader thread, request ids, pending calls, deadlines
  fake/
    server.py         FakeStationServer: TCP front end for FakeStationGateway
  thread_scheduler.py ThreadScheduler: a Scheduler on its own thread (the server's clock)
app/
  qt_post.py          QtPoster: runs a function on the GUI thread (the client's callbacks)
```

`gateway/` stays free of Qt; `test_architecture.py` keeps checking that.

### The method table

One entry per gateway method:

```python
Method("registers.read", "read_register", (Param("pos", int, "position"), Param("name", str)), int)
Method("automation.seq.run", "run_sequence", (...), str, wrap="activity_id")
```

The client turns a call into `method` + `params` from it; the server turns `params` back into arguments and
calls the fake. A test checks that every method on `StationGateway` has exactly one entry, so neither side can
miss one.

## 3. Threads

- **Client.** One reader thread per connection reads frames and hands each one to a `post` function. In the
  app, `post` is `QtPoster`, so replies resolve their `Call` and events are emitted **on the GUI thread**, as
  `gateway/call.py` promises. Writes happen on the calling thread under a lock. The deadline check runs on
  the scheduler the client is given.
- **Server.** Everything the fake does (calls, scheduled ticks, events) runs on one `ThreadScheduler` thread,
  because the fake isn't thread-safe. Socket reader threads only decode frames and post them to it. Replies
  and events are written from that thread, one lock per connection.

## 4. The fake TCP server

`FakeStationServer(fake, scheduler, host="127.0.0.1", port=0)`:

- accepts any number of connections; each has its own event `seq`;
- dispatches requests through the method table, encoding the fake's `Call` result or `ApiError`;
- forwards the fake's events (`fake.events`) to every connection as notifications;
- maps the fake's internal request ids in `timeout` errors and `call.late` events to the JSON-RPC `id`;
- runs standalone: `python -m sirat_ui.gateway.fake.server --port 47800 --scenario happy`.

The fake's test knobs (`fail_next`, `time_out_next`, `drop_dut`, latency...) keep working because they act on
the same `FakeStationGateway`.

## 5. Running the app on it

`sirat --backend`:

- `fake` (default): the in-process fake, as today.
- `api --host H --port P`: connect to a station service (or a standalone fake server) at that address.
- `fake-tcp`: start a `FakeStationServer` in the same process on a free port and connect to it over TCP, so the
  whole app runs over the real wire with one command.

If the connection drops, the client fails every pending call with `internal` ("Lost the connection to the
station"), and every DUT position that was connected gets a `dut.disconnected` event, so the app shows the same
recovery it shows for a dropped DUT. Reconnecting to the station is left for a later step (section 7).

## 6. Tests

- **The 542 existing tests stay on the in-process fake.** They're fast and deterministic, and the chaos runner
  needs exact control of time.
- **New unit tests**: framing (split frames, two frames in one read, oversized frame), the envelope (every
  error code both ways, notifications, batches refused), the codec (every model round-trips).
- **New contract tests** (`tests/contract/`): `ApiStationGateway` against `FakeStationServer` over real TCP:
  - the method table covers `StationGateway` exactly;
  - a few calls per area (sys, dut, registers, rf, instruments, automation, memory, advanced, tests);
  - errors keep their code and data (`wrong_state.missing`, `confirmation_required`);
  - events arrive as `GatewayEvent`s (watch ticks, activity progress and finish, `dut.disconnected`, logs);
  - `timeout` then `call.late` with the JSON-RPC id;
  - a garbled frame, an oversized frame, and the server closing the connection.
- **One end-to-end check**: the app built with `fake-tcp` connects and reads a register.

## 7. Open items (for the station team)

- The doc and this plan now describe JSON-RPC 2.0; the station team needs to agree before building the
  service on it.
- Field differences between the doc's models and the frontend's. The wire follows the frontend for now; one
  side has to change before the real service is built:

  | Doc (`docs/API_DESIGN.md`) | On the wire today (`models/`) |
  |---|---|
  | `RegisterInfo.reset_value: int \| None` | `reset: int` (0 when unknown) |
  | `critical` and `read_sensitive` on `PeripheralInfo` | on each register |
  | registers don't name their peripheral; fields don't name their register | `peripheral` on each register, `register` on each field |
  | `PositionFacts.fault: Fault {cause, detail, at}` | `fault: str` |

- The client has no limit on requests in flight. The app sends one request per user action or poll, so this
  hasn't mattered; a station that answers very slowly would see them pile up until their timeouts.

## 8. Order of work

1. This plan.
2. `docs/API_DESIGN.md`: the protocol section moves to JSON-RPC 2.0 (envelope, codes, events, `_meta`).
3. `gateway/wire/`: framing, envelope, codec, method and event tables, with their unit tests.
4. `ThreadScheduler` and `FakeStationServer`.
5. `ApiStationGateway` and `QtPoster`.
6. Launch options and the contract tests.
7. Full test suite, chaos tests, pyrefly; update `docs/ARCHITECTURE.md`.

## 9. Keeping the link up

What the client and the fake server do so the link survives real use. Tests: `tests/contract/test_link.py`.

**Client (`ApiStationGateway`)**

| Situation | What happens |
|---|---|
| App start | `start()` connects on a background thread, so the GUI never waits. The app's first calls (`sys.hello`, `sys.subscribe`, `sys.status`) are held and sent once the link is up, each within its own timeout. |
| Station not reachable | Held calls fail with "Can't reach the station at host:port". The client retries after 0.5 s, doubling up to 10 s. The log says so once, not on every retry. Calls made while waiting to retry fail at once with the same reason. |
| Link drops | Pending calls fail ("Lost the connection to the station"). Every DUT position the client last saw connected gets a `dut.disconnected`, so the app shows its usual recovery. Then it retries as above. |
| Link back | Subscribes again to the topics it last asked for, refetches `sys.status` and emits it, and logs "Reconnected to the station". DUTs the station kept connected show as connected again. |
| Station silent | After `heartbeat_s` (15 s) with nothing received, it sends `sys.hello`. No reply within about 3 s means the link is dead: it's closed and retried. TCP keepalive is on as well. |
| App closes | `ServiceContainer.stop()` closes the link; no more retries. |

**Fake server (`FakeStationServer`)**

- Events go only to connections that subscribed to their topic (`status`, `activity`, `watch`, `instrument`,
  `log`); an unknown topic is `invalid_params`. `call.late` always goes to the client whose call timed out.
- `_meta.timeout_ms` is enforced: a call still running then is answered `timeout` (`still_running: true`,
  `request_id`), and its outcome follows as `call.late`.
- When a client disconnects, the watch subscriptions and console sessions it opened end, as the API doc says
  for sessions. Activities keep running (`activity.finished` is still sent exactly once).

## 10. Validation at the edge (pydantic)

The wire follows the same rule as the settings files (`stores/schemas`): outside data is validated with pydantic
where it comes in, and only the app's dataclasses go further. `models/` stays free of pydantic.

- `gateway/wire/codec.py` `decode(type, json)` validates with a pydantic `TypeAdapter` for the dataclass type
  and returns the dataclasses themselves; there's no second set of pydantic models to keep in step.
- It runs in pydantic's **strict JSON mode**: arrays are accepted for tuples and whole numbers for floats,
  unknown keys are ignored (a newer station can add fields), but `"5"` or `true` where a number belongs is an
  error. The settings files are deliberately looser (they accept `"0x1F"`), because people edit them by hand.
- The three wire-specific types: `PhySpec` is chosen by its `kind` tag (a pydantic discriminator); `ApiError`
  inside a result validates through its `__get_pydantic_core_schema__` (pydantic is imported only when that
  runs); events rename `pos` back to `position` first, and `registers.watch` is declared as a `TypedDict`.
- Errors keep the plain wording the rest of the wire uses ("pos: must be a whole number", "values[2].name: is
  required").
- The server validates parameters with the same adapters, and the parameter types carry the ranges
  `docs/API_DESIGN.md` gives: `pos` 1–4, `interval_s` 0.1–60, `memory.read` size 1–4096, `memory.write` size
  1/2/4, `config_type` EFX/EFR32, `seconds` 1–300, `siggen.trigger` mode, `console.exec` mode, `eca.result`
  offset ≥ 0 and count ≥ 1. A value outside them is `invalid_params` with `data.param`, before the call runs.
- Cost: decoding the register tree or a two-channel ECA page takes about 0.3 ms.
