"""advanced: Python on the station (console sessions, custom functions) and the DUT control API explorer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from typing_extensions import Literal

from station_protocol.common import POS
from station_protocol.method import Method, Param

ExecMode = Literal["auto", "eval", "exec"]


@dataclass(frozen=True)
class Traceback:
    """A Python error from station-side code."""
    type: str
    message: str
    text: str


@dataclass(frozen=True)
class ExecResult:
    """Console and custom functions. result_text is None when the code had no value."""
    stdout: str = ""
    stderr: str = ""
    result_text: Optional[str] = None
    error: Optional[Traceback] = None


@dataclass(frozen=True)
class NameInfo:
    """A console namespace entry, for help."""
    name: str
    type: str
    doc: str = ""


@dataclass(frozen=True)
class ApiParam:
    """A DUT control method parameter; default_repr is None when it has no default."""
    name: str
    annotation: str
    default_repr: Optional[str]
    required: bool


@dataclass(frozen=True)
class ApiMethod:
    """A DUT control method with its signature and first doc paragraph."""
    name: str
    path: str
    signature: str
    doc: str
    params: Tuple[ApiParam, ...] = ()


@dataclass(frozen=True)
class ApiModule:
    """A DUT control module (lpw.radio) and its methods."""
    name: str
    path: str
    methods: Tuple[ApiMethod, ...] = ()


@dataclass(frozen=True)
class ApiPackage:
    """A DUT control package (LPW) and its modules."""
    name: str
    modules: Tuple[ApiModule, ...] = ()


@dataclass(frozen=True)
class ApiTree:
    """advanced.dut_control.describe's result."""
    packages: Tuple[ApiPackage, ...] = ()


@dataclass(frozen=True)
class InvokeRes:
    """advanced.dut_control.invoke: the result as text, JSON (when it is JSON) and type."""
    result_text: str
    result_json: Any
    result_type: str


SESSION = Param("session_id", str)

METHODS = (
    Method("advanced.console.open", (POS,), str, wrap="session_id", requires=("dut",)),
    Method("advanced.console.exec", (SESSION, Param("code", str), Param("mode", ExecMode, "auto")), ExecResult,
           requires=("dut",)),
    Method("advanced.console.names", (SESSION,), List[NameInfo], wrap="names"),
    Method("advanced.console.close", (SESSION,), None),
    Method("advanced.custom_function", (POS, Param("name", str), Param("code", str),
                                        Param("session_id", Optional[str], None)), ExecResult,
           requires=("dut", "idle")),
    Method("advanced.dut_control.describe", (POS,), ApiTree, requires=("dut",)),
    Method("advanced.dut_control.invoke", (POS, Param("path", str), Param("args", List[Any]),
                                           Param("kwargs", Dict[str, Any])), InvokeRes, requires=("dut", "idle")),
)
