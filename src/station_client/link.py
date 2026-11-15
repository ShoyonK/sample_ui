"""Link: a connection to the station that is kept up on its own. Any tool that talks to the station uses it.

- start() connects on a background thread. Requests made while a connection attempt is running wait for it (up
  to their timeout); requests made while waiting to retry fail at once with the reason.
- If the connection drops, pending requests fail and the link retries with backoff: 0.5 s, doubling, at most
  10 s. Once back it subscribes again to the topics subscribe() last asked for.
- After `heartbeat_s` with nothing from the station, it sends sys.hello; no answer means the link is dead.
- Each notification is passed on with `gap` true when its `seq` shows some were lost (then the owner should
  refetch sys.status).

What it tells its owner (`on_change`): the station couldn't be reached (once per reason, not on every retry),
the link was lost, or it opened (`reconnect` true when it had been open before; the owner refetches what it
shows). Results are raw JSON; checking them against the protocol's types is the owner's (station_protocol).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from station_client.connection import GRACE_MS, Connection, Done
from station_client.timers import Cancellable, Post, Timers
from station_protocol import PROTOCOL_VERSION, jsonrpc
from station_protocol.errors import ApiError, ErrorCode

RETRY_FIRST_S = 0.5
RETRY_MAX_S = 10.0
HEARTBEAT_S = 15.0
HEARTBEAT_TIMEOUT_MS = 3000

# link states
IDLE, CONNECTING, OPEN, WAITING, CLOSED = "idle", "connecting", "open", "waiting", "closed"

# what on_change reports
UNREACHABLE, LOST, OPENED = "unreachable", "lost", "opened"


@dataclass(frozen=True)
class LinkChange:
    kind: str                 # UNREACHABLE, LOST or OPENED
    reason: str = ""          # why (UNREACHABLE, LOST)
    reconnect: bool = False   # OPENED after having been open before


class _NoTimer:
    def cancel(self) -> None:
        pass


@dataclass
class _Held:
    """A request made while a connection attempt was running; sent once it opens."""
    method: str
    params: Dict[str, Any]
    timeout_ms: int
    done: Done
    deadline: Cancellable


class Link:
    """See the module docstring. start() (or open(), which blocks) brings the link up; close() ends it for good.
    `client` is what this tool calls itself in sys.hello."""

    def __init__(self, host: str, port: int, timers: Timers, post: Post, client: str,
                 on_notification: Callable[[jsonrpc.Notification, bool], None],
                 on_change: Callable[[LinkChange], None], protocol: int = PROTOCOL_VERSION,
                 heartbeat_s: float = HEARTBEAT_S, heartbeat_timeout_ms: int = HEARTBEAT_TIMEOUT_MS,
                 retry_first_s: float = RETRY_FIRST_S, retry_max_s: float = RETRY_MAX_S) -> None:
        self.host, self.port = host, port
        self.state = IDLE
        self.reason = "Not connected to the station yet"   # why the link isn't open
        self._timers = timers
        self._post = post
        self._hello = {"client": client, "protocol": protocol}
        self._on_notification = on_notification
        self._on_change = on_change
        self._heartbeat_s = heartbeat_s
        self._heartbeat_timeout_ms = heartbeat_timeout_ms
        self._retry_first_s, self._retry_max_s = retry_first_s, retry_max_s
        self._retry_s = retry_first_s
        self._retry: Optional[Cancellable] = None
        self._was_open = False                        # a later open is a reconnect
        self._topics: Optional[List[str]] = None      # what subscribe() last asked for
        self._held: List[_Held] = []
        self._last_seq = 0
        self._heartbeat_pending = False
        self._conn = self._new_connection()
        self._beat = timers.every(max(100, int(heartbeat_s * 1000 / 3)), lambda: post(self._heartbeat))

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    # ---- the link ----------------------------------------------------------------------------------------

    def _new_connection(self) -> Connection:
        return Connection(self.host, self.port, self._timers, self._post, self._notified, self._closed)

    def open(self) -> None:
        """Connects now, blocking. Raises ApiError(INTERNAL) when the station can't be reached; the link then
        keeps retrying in the background."""
        try:
            self._conn.open()
        except ApiError as exc:
            self._attempt_done(exc)
            raise
        self._attempt_done(None)

    def start(self) -> None:
        """Connects in the background; requests made meanwhile wait for the connection."""
        if self.state in (IDLE, WAITING):
            self.state = CONNECTING
            self._conn = self._new_connection()
            self._conn.open_async(self._attempt_done)

    def close(self) -> None:
        """Ends the link for good: no more retries; pending and held requests fail."""
        self.state, self.reason = CLOSED, "The connection to the station was closed"
        self._beat.cancel()
        if self._retry is not None:
            self._retry.cancel()
        self._fail_held(self.reason)
        self._conn.close()

    def drop(self, reason: str) -> None:
        """Ends the current connection as lost (the link then reconnects)."""
        self._conn.shutdown(reason)

    def _attempt_done(self, error: Optional[ApiError]) -> None:
        if self.state == CLOSED:
            return
        if error is not None:
            first = self.reason != error.message
            self.reason = error.message
            self._fail_held(error.message)
            if first:   # say it once, not on every retry
                self._on_change(LinkChange(UNREACHABLE, error.message))
            self._wait_and_retry()
            return
        self.state, self.reason = OPEN, ""
        self._retry_s = self._retry_first_s
        self._last_seq = 0
        reconnect, self._was_open = self._was_open, True
        held, self._held = self._held, []
        for h in held:
            h.deadline.cancel()
            self._conn.request(h.method, h.params, h.timeout_ms, h.done)
        if reconnect and self._topics is not None:
            self._conn.request("sys.subscribe", {"topics": self._topics}, HEARTBEAT_TIMEOUT_MS, lambda *_: None)
        self._on_change(LinkChange(OPENED, reconnect=reconnect))

    def _wait_and_retry(self) -> None:
        self.state = WAITING
        delay = self._retry_s
        self._retry_s = min(self._retry_s * 2, self._retry_max_s)
        self._retry = self._timers.later(int(delay * 1000), lambda: self._post(self.start))

    def _closed(self, reason: str) -> None:
        if self.state == CLOSED:
            return
        self.reason = reason
        self._on_change(LinkChange(LOST, reason))
        self._wait_and_retry()

    def _heartbeat(self) -> None:
        """Nothing heard for a while: ask; if that goes unanswered too, the link is dead."""
        if self.state != OPEN or self._heartbeat_pending:
            return
        if time.monotonic() - self._conn.last_received < self._heartbeat_s:
            return
        self._heartbeat_pending = True
        conn = self._conn

        def done(_: Any, error: Optional[ApiError]) -> None:
            self._heartbeat_pending = False
            if error is not None and error.data.get("client_side") and conn is self._conn:   # no reply at all
                conn.shutdown("The station stopped answering")

        # the connection waits timeout_ms + GRACE_MS, so this gives up after about heartbeat_timeout_ms
        conn.request("sys.hello", self._hello, max(100, self._heartbeat_timeout_ms - GRACE_MS), done)

    def _fail_held(self, reason: str) -> None:
        held, self._held = self._held, []
        for h in held:
            h.deadline.cancel()
            h.done(None, ApiError(ErrorCode.INTERNAL, reason))

    # ---- requests ----------------------------------------------------------------------------------------

    def request(self, method: str, params: Dict[str, Any], timeout_ms: int, done: Done) -> None:
        """Sends a request (or holds it while connecting); `done(result, error)` is called exactly once."""
        if self.state == OPEN:
            self._conn.request(method, params, timeout_ms, done)
        elif self.state == CONNECTING:
            held = _Held(method, params, timeout_ms, done, _NoTimer())
            held.deadline = self._timers.later(timeout_ms + GRACE_MS, lambda: self._post(lambda: self._expire(held)))
            self._held.append(held)
        else:
            done(None, ApiError(ErrorCode.INTERNAL, self.reason or "Not connected to the station"))

    def subscribe(self, topics: List[str], timeout_ms: int, done: Done) -> None:
        """sys.subscribe, remembered so the link asks for the same topics again after a reconnect."""
        self._topics = list(topics)
        self.request("sys.subscribe", {"topics": list(topics)}, timeout_ms, done)

    def _expire(self, held: _Held) -> None:
        if held in self._held:
            self._held.remove(held)
            held.done(None, ApiError(ErrorCode.TIMEOUT, f"Still connecting to the station; {held.method} wasn't sent",
                                     {"still_running": False, "client_side": True}))

    # ---- events ------------------------------------------------------------------------------------------

    def _notified(self, note: jsonrpc.Notification) -> None:
        gap = bool(self._last_seq) and note.seq > self._last_seq + 1
        self._last_seq = max(self._last_seq, note.seq)
        self._on_notification(note, gap)
