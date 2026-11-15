"""Connection: one TCP connection to the station, with its requests in flight.

A reader thread turns bytes into frames and hands each frame to `post`, which runs it on the owner's thread (in
the SiBench GUI, the GUI thread). Everything else (sending, matching replies, deadlines, the closed state) happens
on that thread too, so only the socket is shared with the reader.

A request's outcome arrives through its `done(result, error)` callback: the raw JSON result and None, or None and
an ApiError. It is called exactly once.
"""

from __future__ import annotations

import itertools
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from station_client.timers import Cancellable, Post, Timers
from station_protocol import jsonrpc
from station_protocol.errors import ApiError, ErrorCode
from station_protocol.framing import FrameError, FrameReader, decode_body, encode_frame

GRACE_MS = 2000   # how long past timeout_ms the client waits for the station's own timeout reply

Done = Callable[[Any, Optional[ApiError]], None]


@dataclass
class _Pending:
    done: Done
    method: str
    deadline: Cancellable


class Connection:
    """See the module docstring. `on_notification` gets each event; `on_closed(reason)` runs once when the
    connection ends, after every pending request has failed."""

    def __init__(self, host: str, port: int, timers: Timers, post: Post,
                 on_notification: Callable[[jsonrpc.Notification], None],
                 on_closed: Callable[[str], None], connect_timeout_s: float = 5.0) -> None:
        self.host, self.port = host, port
        self._timers = timers
        self._post = post
        self._on_notification = on_notification
        self._on_closed = on_closed
        self._connect_timeout_s = connect_timeout_s
        self._sock: Optional[socket.socket] = None
        self._send_lock = threading.Lock()
        self._ids = itertools.count(1)
        self._pending: Dict[int, _Pending] = {}
        self.closed_reason = ""          # set once the connection has ended
        self.last_received = 0.0         # time.monotonic() of the last bytes from the station (the heartbeat)
        self._closing = False

    @property
    def is_open(self) -> bool:
        return self._sock is not None and not self.closed_reason

    def open(self) -> None:
        """Connects, blocking the calling thread. Raises ApiError(INTERNAL) when the station can't be reached;
        requests then fail with that reason."""
        self._opened(self._connect())

    def open_async(self, on_done: Callable[[Optional[ApiError]], None]) -> None:
        """Connects on a thread of its own, so the owner's thread never waits for it; on_done(None or the error)
        is posted back."""
        def attempt() -> None:
            try:
                sock = self._connect()
            except ApiError as exc:
                self._post(lambda error=exc: on_done(error))   # bound now: `exc` is gone after the except block
                return
            self._post(lambda: self._finish_open(sock, on_done))
        threading.Thread(target=attempt, name="station-connect", daemon=True).start()

    def _finish_open(self, sock: socket.socket, on_done: Callable[[Optional[ApiError]], None]) -> None:
        if self._closing:   # closed while the attempt was running
            sock.close()
            on_done(ApiError(ErrorCode.INTERNAL, self.closed_reason or "The connection was closed"))
            return
        self._opened(sock)
        on_done(None)

    def _connect(self) -> socket.socket:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self._connect_timeout_s)
        except OSError as exc:
            self.closed_reason = f"Can't reach the station at {self.host}:{self.port}: {exc}"
            raise ApiError(ErrorCode.INTERNAL, self.closed_reason, {"station": f"{self.host}:{self.port}"}) from None
        sock.settimeout(None)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)   # the OS notices a peer that vanished
        return sock

    def _opened(self, sock: socket.socket) -> None:
        self._sock = sock
        self.closed_reason = ""
        self.last_received = time.monotonic()
        threading.Thread(target=self._read_loop, args=(sock,), name="station-reader", daemon=True).start()

    def shutdown(self, reason: str) -> None:
        """Ends the connection as lost (on_closed runs): e.g. the heartbeat found the station stopped answering."""
        self._shutdown(reason)

    def close(self) -> None:
        """Closes the connection on purpose. Pending requests fail; on_closed doesn't run."""
        self._closing = True
        self._shutdown("The connection to the station was closed")

    # ---- requests (owner's thread) ----------------------------------------------------------------------------

    def request(self, method: str, params: Dict[str, Any], timeout_ms: int, done: Done) -> None:
        """Sends one request; `done` gets the raw JSON result or an ApiError."""
        if not self.is_open:
            done(None, ApiError(ErrorCode.INTERNAL, self.closed_reason or "Not connected to the station"))
            return
        request_id = next(self._ids)
        deadline = self._timers.later(timeout_ms + GRACE_MS, lambda: self._post(lambda: self._expire(request_id)))
        self._pending[request_id] = _Pending(done, method, deadline)
        try:
            frame = encode_frame(jsonrpc.request(request_id, method, params, timeout_ms))
        except (FrameError, TypeError, ValueError) as exc:
            self._settle(request_id, error=ApiError(ErrorCode.INVALID_PARAMS, f"Can't send {method}: {exc}"))
            return
        try:
            with self._send_lock:
                assert self._sock is not None
                self._sock.sendall(frame)
        except OSError as exc:
            self._shutdown(f"Lost the connection to the station: {exc}")

    def _expire(self, request_id: int) -> None:
        pending = self._pending.get(request_id)
        if pending is not None:
            self._settle(request_id, error=ApiError(
                ErrorCode.TIMEOUT, f"The station didn't answer {pending.method} in time",
                {"still_running": None, "client_side": True, "request_id": request_id}))

    def _settle(self, request_id: Any, result: Any = None, error: Optional[ApiError] = None) -> None:
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return   # a reply that came after the client gave up, or an id that was never ours
        pending.deadline.cancel()
        pending.done(result if error is None else None, error)

    # ---- incoming (reader thread, then owner's thread) ---------------------------------------------------------

    def _read_loop(self, sock: socket.socket) -> None:
        reader = FrameReader()
        reason = "The station closed the connection"
        try:
            while True:
                data = sock.recv(65536)
                if not data:
                    break
                self.last_received = time.monotonic()
                for body in reader.feed(data):
                    self._post(lambda b=body: self._dispatch(b))
        except FrameError as exc:
            reason = f"The station sent a frame that can't be read ({exc})"
        except OSError as exc:
            reason = f"Lost the connection to the station: {exc}"
        self._post(lambda: self._shutdown(reason))

    def _dispatch(self, body: bytes) -> None:
        try:
            message = jsonrpc.read_incoming(decode_body(body))
        except (FrameError, jsonrpc.ProtocolError) as exc:
            self._shutdown(f"The station sent a message that isn't JSON-RPC 2.0 ({exc})")
            return
        if isinstance(message, jsonrpc.Notification):
            self._on_notification(message)
        else:
            self._settle(message.id, message.result, message.error)

    def _shutdown(self, reason: str) -> None:
        if self.closed_reason:
            return
        self.closed_reason = reason
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        for request_id in list(self._pending):
            self._settle(request_id, error=ApiError(ErrorCode.INTERNAL, reason))
        if not self._closing:
            self._on_closed(reason)
