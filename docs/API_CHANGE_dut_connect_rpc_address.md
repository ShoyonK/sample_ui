# API change proposal: per-connection RPC address on `dut.connect`

> **Superseded** by [API_DESIGN.md](API_DESIGN.md) (revision 2), which folds this proposal in. Kept for the reasoning.

**For:** SiRAT Station API: Design Document (section "API by domain → dut")
**Status:** Proposed. The SiRAT frontend and its fake backend already implement it.
**Date:** 2026-10-27

## Why

SiRAT requirement §32 (Hardware Configuration) lets the user set the DUT's RPC host and port. In the
original GUI this was the address the GUI itself connected to.

In the Station API design, the GUI never talks to the DUT. The station service connects, and takes
each position's RPC address from the workspace config. The API has no way to pass an address, so
§32's host and port would have no effect.

Some users still need to reach a DUT that isn't in the workspace config, for example a board on a
desk at another IP while bringing up a station. The workspace config should stay the default and the
single source of truth for the bench. An override should be explicit and apply to one connection only.

## Change

Add two optional parameters to `dut.connect`:

```
dut.connect(pos, config_type, config_file,
            rpc_host: str | None = None,
            rpc_port: int | None = None)
   -> ConnectResult: chip, rpc_ok
   requires: no_fault
```

| Parameter | Meaning |
|---|---|
| `rpc_host` | Host name or IP of the DUT's RPC server. `None`: use the workspace config (today's behaviour). |
| `rpc_port` | Port, 1–65535. `None` with a host: the workspace config's port for that position. |

Contract model (`contracts/dut.py`):

```python
class ConnectReq(Model):
    position: Position
    config_type: str
    config_file: str = ""
    rpc_host: str | None = None
    rpc_port: Annotated[int, Field(ge=1, le=65535)] | None = None
```

## Rules

1. **Scope.** The override applies to that connection only. It isn't saved by the service and doesn't
   change the workspace config. A later `dut.connect` without it goes back to the workspace config.
2. **Validation.**
   - An empty or whitespace-only `rpc_host` fails with `invalid_params`.
   - An out-of-range `rpc_port` fails schema validation (`invalid_params`).
3. **Unreachable address.** No answer within the RPC timeout fails with `timeout`, carrying
   `"No answer from {host}:{port}"` in `message`. A refused connection maps to `dut_disconnected`
   (link never came up) or `hardware_error`, per the existing mapping rules.
4. **Reconnect.** The service doesn't remember overrides. Clients that reconnect (SiRAT's disconnect
   recovery) send the same parameters again. SiRAT already does this.
5. **Visibility.** `dut.info` returns the address actually in use in `rta.host` / `rta.port`, so
   clients can show where a position is really connected.
6. **Logging.** The service logs overrides with the client id, like `advanced.py_exec` calls, since an
   override can point a position at a different board.
7. **Claims.** No change. Whoever holds the station's claim can connect, with or without an override.

## Open questions for the API owners

- Should overrides be allowed only when the station isn't claimed by an automated run?
- Should the workspace config be able to forbid overrides per station (e.g. production stations)?

## Frontend behaviour (already built)

- **Settings → Hardware configuration:**
  - The "Use a specific RPC address" checkbox is off by default. Off means nothing is sent and the
    workspace config decides.
  - Host and port are validated per §32 only while it's on.
  - Values are saved in `~/.sirat/hardware_config.json` with an added `rpc_override` key. The old GUI
    ignores unknown keys.
- **Connect sheet:**
  - The same checkbox, host and port, pre-filled from Settings.
  - Changes there apply to that one connection.
- **Test connection** uses the address when the box is checked, and disconnects afterwards.
- **System information → RPC Information** shows `rta.host` / `rta.port` from `dut.info`.
- **The fake backend:**
  - Implements the rules above.
  - Uses `localhost:10001` as its "workspace config".
  - Treats hosts ending in `.invalid` and `10.255.255.1` as unreachable (timeout), so the failure path
    is testable.
