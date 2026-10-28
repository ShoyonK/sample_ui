"""Call: the async result of one gateway request.

Callbacks run on whatever thread resolves the call. The real gateway resolves on the GUI thread;
the fake resolves synchronously or through its scheduler.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, List, Optional, TypeVar

from sirat_ui.gateway.errors import ApiError, ErrorCode

T = TypeVar("T")
U = TypeVar("U")


class Call(Generic[T]):
    def __init__(self) -> None:
        self._state = "pending"
        self._result: Optional[T] = None
        self._error: Optional[ApiError] = None
        self._on_ok: List[Callable[[T], Any]] = []
        self._on_err: List[Callable[[ApiError], None]] = []

    @staticmethod
    def succeeded(result: U = None) -> "Call[U]":  # type: ignore[assignment]
        call: Call[U] = Call()
        call.resolve(result)
        return call

    @staticmethod
    def failed(error: ApiError) -> "Call[Any]":
        call: Call[Any] = Call()
        call.reject(error)
        return call

    @property
    def pending(self) -> bool:
        return self._state == "pending"

    @property
    def ok(self) -> bool:
        return self._state == "ok"

    @property
    def result(self) -> Optional[T]:
        return self._result

    @property
    def error(self) -> Optional[ApiError]:
        return self._error

    def then(self, on_ok: Optional[Callable[[T], Any]] = None,
             on_err: Optional[Callable[[ApiError], None]] = None) -> "Call[T]":
        if on_ok:
            if self._state == "ok":
                on_ok(self._result)  # type: ignore[arg-type]  # resolved, so this is the T it was resolved with
            elif self._state == "pending":
                self._on_ok.append(on_ok)
        if on_err:
            if self._state == "error":
                on_err(self._error)  # type: ignore[arg-type]
            elif self._state == "pending":
                self._on_err.append(on_err)
        return self

    def resolve(self, result: T = None) -> None:  # type: ignore[assignment]
        if self._state != "pending":
            return
        self._state, self._result = "ok", result
        for callback in self._on_ok:
            callback(result)
        self._on_ok.clear()
        self._on_err.clear()

    def reject(self, error: ApiError) -> None:
        if self._state != "pending":
            return
        if not isinstance(error, ApiError):
            error = ApiError(ErrorCode.INTERNAL, str(error))
        self._state, self._error = "error", error
        for callback in self._on_err:
            callback(error)
        self._on_ok.clear()
        self._on_err.clear()

    def map(self, fn: Callable[[T], U]) -> "Call[U]":
        out: Call[U] = Call()

        def on_ok(result: T) -> None:
            try:
                out.resolve(fn(result))
            except ApiError as exc:
                out.reject(exc)

        self.then(on_ok, out.reject)
        return out
