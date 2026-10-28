"""memory.* and advanced.* for the fake station (req 15, 19, 20, 22).

FakeAdvanced does the work and gets what it needs from the station explicitly; AdvancedMethods gives
FakeStationGateway the gateway methods, each a one-line call into its FakeAdvanced.

Console sessions keep a namespace per session (dut, a few utilities, and whatever the user defines) until
they're closed or their DUT disconnects. Custom functions use a session's namespace when given one. DUT
control introspects gateway/fake/dut_api.py, the same object the console calls `dut`.

Test knobs (on station.advanced): exec_time_limit_s, sessions, duts.
"""

from __future__ import annotations

import base64
import inspect
import itertools
import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError, ErrorCode
from sirat_ui.gateway.fake import dut_api, python_runner
from sirat_ui.gateway.fake.dut_api import FakeDut, RailAssert, RpcTimeout, RpcTransportError
from sirat_ui.gateway.fake.memory import FakeMemory
from sirat_ui.gateway.fake.register_memory import RegisterMemory
from sirat_ui.models.registers import ChipInfo, PeripheralDef
from sirat_ui.models.station import ApiTree, ExecResult, InvokeRes, MemoryBlock, MemoryWriteRes, NameInfo


def wait_ms(ms: float) -> None:
    """Sleep for ms milliseconds."""
    time.sleep(ms / 1000)


def to_hex(value: int, width: int = 8) -> str:
    """Format an int as 0x-prefixed hex, zero-padded to width digits."""
    return f"0x{value:0{width}X}"


UTILITIES: Dict[str, Any] = {"time": time, "math": math, "struct": struct, "wait_ms": wait_ms, "to_hex": to_hex}
CAUSES = ((RpcTimeout, "rpc_timeout"), (RpcTransportError, "rpc_transport"), (RailAssert, "rail_assert"))


@dataclass
class ConsoleSession:
    session_id: str
    position: int
    namespace: Dict[str, Any] = field(default_factory=dict)


class AdvancedHost(Protocol):
    """What FakeAdvanced reads from the station: register values, the chip, and the RPC timeout dut.rta sets."""
    memory: RegisterMemory
    chip: ChipInfo
    rpc_timeout_s: float


Respond = Callable[..., Call]
Log = Callable[..., None]


class FakeAdvanced:
    def __init__(self, respond: Respond, log: Log, host: AdvancedHost, peripherals: List[PeripheralDef],
                 seed: int) -> None:
        self._respond = respond
        self._log = log
        self._host = host
        self.ram = FakeMemory(peripherals, host.memory, seed)
        self.sessions: Dict[str, ConsoleSession] = {}
        self.exec_time_limit_s = 2.0
        self.duts: Dict[int, FakeDut] = {}
        self._session_ids = itertools.count(1)
        self._run_namespaces: Dict[int, Dict[str, Any]] = {}

    # FakeDut's host (gateway/fake/dut_api.py DutHost): the station's registers and chip, this RAM
    @property
    def memory(self) -> RegisterMemory:
        return self._host.memory

    @property
    def chip(self) -> ChipInfo:
        return self._host.chip

    @property
    def rpc_timeout_s(self) -> float:
        return self._host.rpc_timeout_s

    @rpc_timeout_s.setter
    def rpc_timeout_s(self, seconds: float) -> None:
        self._host.rpc_timeout_s = seconds

    def dut(self, position: int) -> FakeDut:
        if position not in self.duts:
            self.duts[position] = FakeDut(self, position)
        return self.duts[position]

    def _namespace(self, position: int) -> Dict[str, Any]:
        return {"dut": self.dut(position), **UTILITIES}

    def end_sessions(self, position: int) -> None:
        """API doc: a session ends when its DUT disconnects."""
        for sid in [s for s, session in self.sessions.items() if session.position == position]:
            del self.sessions[sid]
        self.duts.pop(position, None)

    def _session(self, session_id: str) -> ConsoleSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise ApiError(ErrorCode.NOT_FOUND, f"Console session {session_id} has ended", {"session_id": session_id})
        return session

    # ---- memory -------------------------------------------------------------------------------------------

    def memory_read(self, position: int, address: int, size: int) -> Call[MemoryBlock]:
        def run() -> MemoryBlock:
            start, data = self.ram.read(address, size)
            return MemoryBlock(start, base64.b64encode(data).decode())
        return self._respond("memory.read", position, run, address=address, size=size)

    def memory_write(self, position: int, address: int, value: int, size: int) -> Call[MemoryWriteRes]:
        def run() -> MemoryWriteRes:
            readback = self.ram.write(address, value, size)
            self._log("info", f"Memory write 0x{value:0{size * 2}X} to 0x{address:08X}", position=position)
            return MemoryWriteRes(address, value, readback)
        return self._respond("memory.write", position, run, address=address, value=value, size=size)

    # ---- console --------------------------------------------------------------------------------------------

    def console_open(self, position: int) -> Call[str]:
        def run() -> str:
            sid = f"py{next(self._session_ids)}"
            self.sessions[sid] = ConsoleSession(sid, position, self._namespace(position))
            return sid
        return self._respond("advanced.console.open", position, run)

    def console_exec(self, session_id: str, code: str, mode: str = "auto") -> Call[ExecResult]:
        session = self.sessions.get(session_id)
        position = session.position if session else None

        def run() -> ExecResult:
            if mode not in ("auto", "eval", "exec"):
                raise ApiError(ErrorCode.INVALID_PARAMS, "mode is auto, eval or exec")
            return python_runner.run(code, self._session(session_id).namespace, mode,
                                     time_limit_s=self.exec_time_limit_s)
        return self._respond("advanced.console.exec", position, run, session_id=session_id, code=code, mode=mode)

    def console_names(self, session_id: str) -> Call[List[NameInfo]]:
        def run() -> List[NameInfo]:
            namespace = self._session(session_id).namespace
            return [NameInfo(name, type(value).__name__, ((getattr(value, "__doc__", "") or "").strip()
                                                          .split("\n")[0] if callable(value) else ""))
                    for name, value in sorted(namespace.items()) if not name.startswith("_")]
        return self._respond("advanced.console.names", None, run, session_id=session_id)

    def console_close(self, session_id: str) -> Call[None]:
        def run() -> None:
            self.sessions.pop(session_id, None)
        return self._respond("advanced.console.close", None, run, session_id=session_id)

    # ---- custom functions -------------------------------------------------------------------------------------

    def custom_function(self, position: int, name: str, code: str,
                        session_id: Optional[str] = None) -> Call[ExecResult]:
        def run() -> ExecResult:
            namespace = self._session(session_id).namespace if session_id else self._namespace(position)
            self._log("info", f"Ran custom function {name}", position=position)
            return python_runner.run(code, namespace, "auto", function_name=name, time_limit_s=self.exec_time_limit_s)
        return self._respond("advanced.custom_function", position, run, name=name, code=code, session_id=session_id)

    # ---- DUT control ------------------------------------------------------------------------------------------

    def dut_control_describe(self, position: int) -> Call[ApiTree]:
        return self._respond("advanced.dut_control.describe", position, dut_api.describe)

    def dut_control_invoke(self, position: int, path: str, args: List[Any],
                           kwargs: Dict[str, Any]) -> Call[InvokeRes]:
        def run() -> InvokeRes:
            value = self._invoke(position, path, args, kwargs)
            self._log("info", f"Called {path}", position=position)
            json_value = value if isinstance(value, (type(None), bool, int, float, str, list, dict)) else None
            return InvokeRes(dut_api.format_result(value), json_value, type(value).__name__)
        return self._respond("advanced.dut_control.invoke", position, run, path=path, args=list(args),
                             kwargs=dict(kwargs))

    def _invoke(self, position: int, path: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        dut = self.dut(position)
        method = dut.method(path)
        if method is None:
            raise ApiError(ErrorCode.NOT_FOUND, f"{path} isn't in the DUT control API")
        if "dut" in inspect.signature(method).parameters:
            kwargs = {"dut": dut, **kwargs}
        try:
            inspect.signature(method).bind(*args, **kwargs)
        except TypeError as exc:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"{path}: {exc}") from None
        try:
            return method(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 (any DUT failure becomes hardware_error)
            cause = next((c for cls, c in CAUSES if isinstance(exc, cls)), "other")
            tb = python_runner.format_traceback(exc)
            raise ApiError(ErrorCode.HARDWARE_ERROR, f"{type(exc).__name__}: {exc}",
                           {"cause": cause, "traceback": tb.text}) from None

    # ---- ops in automation.seq.run ------------------------------------------------------------------------------

    def new_run_namespace(self, position: int) -> None:
        """API doc: ops in one run share one Python namespace."""
        self._run_namespaces[position] = self._namespace(position)

    def run_op(self, position: int, kind: str, op: Dict[str, Any]) -> Any:
        if kind == "dut_control_method":
            return self._invoke(position, str(op.get("method_path")), [], dict(op.get("params") or {}))
        name = str(op.get("function_name"))
        if not op.get("code"):
            raise ApiError(ErrorCode.INVALID_PARAMS, f"custom function {name} has no code")
        namespace = self._run_namespaces.setdefault(position, self._namespace(position))
        result = python_runner.run(str(op["code"]), namespace, "auto", function_name=name,
                                   time_limit_s=self.exec_time_limit_s)
        if result.error is not None:
            raise ApiError(ErrorCode.HARDWARE_ERROR, f"{name}: {result.error.type}: {result.error.message}",
                           {"cause": "other", "traceback": result.error.text})
        return result.result_text


class AdvancedMethods:
    """FakeStationGateway's memory.* and advanced.* methods; the work is in its FakeAdvanced."""
    advanced: FakeAdvanced

    def memory_read(self, position: int, address: int, size: int) -> Call[MemoryBlock]:
        return self.advanced.memory_read(position, address, size)

    def memory_write(self, position: int, address: int, value: int, size: int) -> Call[MemoryWriteRes]:
        return self.advanced.memory_write(position, address, value, size)

    def console_open(self, position: int) -> Call[str]:
        return self.advanced.console_open(position)

    def console_exec(self, session_id: str, code: str, mode: str = "auto") -> Call[ExecResult]:
        return self.advanced.console_exec(session_id, code, mode)

    def console_names(self, session_id: str) -> Call[List[NameInfo]]:
        return self.advanced.console_names(session_id)

    def console_close(self, session_id: str) -> Call[None]:
        return self.advanced.console_close(session_id)

    def custom_function(self, position: int, name: str, code: str,
                        session_id: Optional[str] = None) -> Call[ExecResult]:
        return self.advanced.custom_function(position, name, code, session_id)

    def dut_control_describe(self, position: int) -> Call[ApiTree]:
        return self.advanced.dut_control_describe(position)

    def dut_control_invoke(self, position: int, path: str, args: List[Any],
                           kwargs: Dict[str, Any]) -> Call[InvokeRes]:
        return self.advanced.dut_control_invoke(position, path, args, kwargs)
