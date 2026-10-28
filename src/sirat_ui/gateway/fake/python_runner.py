"""Runs console code and custom functions for the fake station, the way the API doc describes the service.

- auto tries eval and falls back to exec on SyntaxError (req 20).
- Custom functions run wrapped in a function so a top-level `return` works; names they assign are declared
  global, so variables still persist in the shared namespace (req 15).
- stdout and stderr are captured, and the traceback shows only the user's own frames.
- A time limit stops runaway loops, which would otherwise freeze the GUI (the fake runs in-process).
"""

from __future__ import annotations

import ast
import contextlib
import io
import sys
import time
import traceback
from typing import Any, Dict, Optional, Set

from sirat_ui.models.station import ExecResult, Traceback

_FN = "__sirat_custom_function__"


class _TimeLimit(BaseException):  # not Exception, so `except Exception` in user code can't swallow it
    pass


def _stored_names(body: list) -> Set[str]:
    """Names a function body binds, not counting nested functions, classes and lambdas."""
    names: Set[str] = set()
    stack = list(body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            continue
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split(".")[0] for a in node.names if a.name != "*")
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        stack.extend(ast.iter_child_nodes(node))
    return names


def _has_top_level_return(tree: ast.Module) -> bool:
    stack: list = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return):
            return True
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))
    return False


def _as_function(tree: ast.Module, filename: str) -> Any:
    """def __fn__(): global <assigned names>; <body> — line numbers stay those of the user's code."""
    body = list(tree.body)
    names = sorted(_stored_names(body))
    if names:
        body.insert(0, ast.Global(names=names, lineno=1, col_offset=0))
    fn = ast.FunctionDef(name=_FN, args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[],
                                                      defaults=[]),
                         body=body, decorator_list=[], returns=None, lineno=1, col_offset=0)
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    return compile(module, filename, "exec")


def format_traceback(exc: BaseException) -> Traceback:
    te = traceback.TracebackException.from_exception(exc)
    te.stack = traceback.StackSummary.from_list([f for f in te.stack if f.filename.startswith("<")])
    return Traceback(type(exc).__name__, str(exc), "".join(te.format()).rstrip())


def run(code: str, namespace: Dict[str, Any], mode: str = "auto", function_name: Optional[str] = None,
        time_limit_s: float = 2.0) -> ExecResult:
    out, err = io.StringIO(), io.StringIO()
    filename = f"<{function_name}>" if function_name else "<console>"
    namespace.setdefault("__builtins__", __builtins__)
    deadline = time.monotonic() + time_limit_s

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        if event == "call":
            frame.f_trace_opcodes = True   # a one-line `while True: pass` never fires a line event
        if time.monotonic() > deadline:
            raise _TimeLimit(f"Stopped after {time_limit_s:g} s")
        return tracer

    value: Any = None
    error: Optional[Traceback] = None
    previous = sys.gettrace()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            sys.settrace(tracer)
            try:
                value = _run(code, namespace, mode, function_name, filename)
            finally:
                sys.settrace(previous)
    except _TimeLimit as exc:
        error = Traceback("TimeoutError", str(exc), f"TimeoutError: {exc} (the fake station's limit)")
    except BaseException as exc:  # noqa: BLE001 (user code may raise anything, SystemExit included)
        error = format_traceback(exc)
    if function_name and error is None:
        namespace["last_dut_api_result"] = value
        namespace[f"result_{function_name}"] = value
    result_text = None if value is None or error is not None else repr(value)
    return ExecResult(out.getvalue(), err.getvalue(), result_text, error)


def _run(code: str, namespace: Dict[str, Any], mode: str, function_name: Optional[str], filename: str) -> Any:
    if mode in ("auto", "eval"):
        try:
            expression = compile(code, filename, "eval")
        except SyntaxError:
            if mode == "eval":
                raise
        else:
            return eval(expression, namespace)  # noqa: S307 (this is the console)
    tree = ast.parse(code, filename, "exec")
    if function_name and _has_top_level_return(tree):
        exec(_as_function(tree, filename), namespace)  # noqa: S102
        try:
            return namespace[_FN]()
        finally:
            namespace.pop(_FN, None)
    exec(compile(tree, filename, "exec"), namespace)  # noqa: S102
    return None
