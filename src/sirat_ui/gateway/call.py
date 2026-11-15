"""Call: the async result of one gateway request.

Callbacks run on whatever thread resolves the call. The real gateway resolves on the GUI thread;
the fake resolves synchronously or through its scheduler.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, List, Optional, TypeVar

from sirat_ui.gateway.errors import ApiError, ErrorCode

T = TypeVar("T")
U = TypeVar("U")

_PENDING, _OK, _ERROR = "pending", "ok", "error"


class Call(Generic[T]):
    """A result that arrives later: it resolves once with a value or rejects once with an ApiError.

    Callbacks added with then() before it settles run when it settles; added after, they run at once.
    """

    def __init__(self) -> None:
        self._state = _PENDING
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
        return self._state == _PENDING

    @property
    def ok(self) -> bool:
        return self._state == _OK

    @property
    def result(self) -> Optional[T]:
        return self._result

    @property
    def error(self) -> Optional[ApiError]:
        return self._error

    def then(self, on_ok: Optional[Callable[[T], Any]] = None,
             on_err: Optional[Callable[[ApiError], None]] = None) -> "Call[T]":
        """Adds callbacks and returns this same call (not a new one; see map() for chaining a value).

        Args:
            on_ok: Called with the result when (or if already) resolved.
            on_err: Called with the error when (or if already) rejected.
        """
        if on_ok:
            if self._state == _OK:
                on_ok(self._result)  # type: ignore[arg-type]  # resolved, so this is the T it was resolved with
            elif self._state == _PENDING:
                self._on_ok.append(on_ok)
        if on_err:
            if self._state == _ERROR:
                on_err(self._error)  # type: ignore[arg-type]
            elif self._state == _PENDING:
                self._on_err.append(on_err)
        return self

    def resolve(self, result: T = None) -> None:  # type: ignore[assignment]
        """Settles the call with a value; later resolve() or reject() calls are ignored."""
        if self._state != _PENDING:
            return
        self._state, self._result = _OK, result
        for callback in self._on_ok:
            callback(result)
        self._on_ok.clear()
        self._on_err.clear()

    def reject(self, error: ApiError) -> None:
        """Settles the call with an error; later resolve() or reject() calls are ignored."""
        if self._state != _PENDING:
            return
        if not isinstance(error, ApiError):   # a plain exception passed through by mistake still reaches on_err
            error = ApiError(ErrorCode.INTERNAL, str(error))
        self._state, self._error = _ERROR, error
        for callback in self._on_err:
            callback(error)
        self._on_ok.clear()
        self._on_err.clear()

    def map(self, fn: Callable[[T], U]) -> "Call[U]":
        """A new call that resolves with fn(result), or rejects with this call's error.

        fn may raise ApiError to reject the new call. Any other exception isn't caught: it propagates to whoever
        resolved this call, so a bug in fn isn't hidden as an API error.
        """
        out: Call[U] = Call()

        def on_ok(result: T) -> None:
            try:
                out.resolve(fn(result))
            except ApiError as exc:
                out.reject(exc)

        self.then(on_ok, out.reject)
        return out
