"""The Station API on the wire: what every client and the station service share (docs/STATION_API.md).

Framing (framing.py), the JSON-RPC 2.0 envelope and error codes (jsonrpc.py, errors.py), validation (validate.py),
and one module per method group (system.py is `sys`, dut.py, registers.py...), each with its methods,
parameter and result types, and events. catalog.py collects them all.

This package imports nothing from any application: a GUI, the debug harness and the station service all depend
on it, and it is meant to move to the station's repository as a published package. tests/unit/test_architecture.py
checks it stays that way.
"""

PROTOCOL_VERSION = 2   # what sys.hello's `protocol` carries: 2 is JSON-RPC 2.0
