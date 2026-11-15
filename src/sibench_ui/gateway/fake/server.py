"""FakeStationServer: the fake station behind a real TCP socket, speaking JSON-RPC 2.0 (docs/JSONRPC_MIGRATION.md).

It lets ApiStationGateway be built and tested before the station service exists. Every request is decoded with
the protocol's method table (station_protocol), checked with its parameter types, run on the FakeStationGateway, and answered; the fake's events go to
every connection as notifications, each connection with its own `seq`.

Threads: one accepts connections and one reads each connection. They only turn bytes into frames and post them
to the ThreadScheduler, where everything the fake does runs, so the fake is only ever used from one thread.

Run standalone:  python -m sibench_ui.gateway.fake.server --port 47800 --scenario happy
"""

from __future__ import annotations

import argparse
import itertools
import socket
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from station_protocol import jsonrpc
from station_protocol.catalog import BY_EVENT, TOPICS
from station_protocol.framing import FrameError, FrameReader, decode_body, encode_frame
from station_protocol.method import check_params, wrap_result
from sibench_ui.gateway.call import Call
from sibench_ui.gateway.errors import ApiError, ErrorCode
from sibench_ui.gateway.fake.fake_station import FakeStationGateway
from sibench_ui.gateway.fake.scenarios import Scenario, apply_scenario
from sibench_ui.gateway.thread_scheduler import ThreadScheduler
from sibench_ui.gateway.wire.bindings import BY_WIRE_NAME, Binding
from sibench_ui.gateway.wire.codec import CodecError, decode, to_wire
from sibench_ui.gateway.wire.events import NAMES, encode_event
from sibench_ui.models.station import CallLate

DEFAULT_PORT = 47800


class _Connection:
    """One client: its socket, its event counter, and a lock so replies and events don't interleave."""

    _ids = itertools.count(1)

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.number = next(self._ids)
        self.seq = itertools.count(1)
        self.open = True
        self.topics: Set[str] = set()     # sys.subscribe: which events this client gets
        self.watches: Set[str] = set()    # watch subscriptions it opened; ended when it disconnects
        self.sessions: Set[str] = set()   # console sessions it opened; closed when it disconnects
        self._lock = threading.Lock()

    def send(self, message: Dict[str, Any]) -> None:
        if not self.open:
            return
        try:
            frame = encode_frame(message)
        except FrameError as exc:   # a result too big for one frame: say so instead of dropping the call
            if message.get("id") is None:
                return
            frame = encode_frame(jsonrpc.error_reply(message["id"], jsonrpc.error_object(
                ApiError(ErrorCode.INTERNAL, str(exc)))))
        try:
            with self._lock:
                self.sock.sendall(frame)
        except OSError:
            self.close()

    def close(self) -> None:
        self.open = False
        try:
            self.sock.close()
        except OSError:
            pass


class FakeStationServer:
    """See the module docstring. start() binds and listens; `address` is where (port 0 picks a free one)."""

    def __init__(self, fake: FakeStationGateway, scheduler: ThreadScheduler, host: str = "127.0.0.1",
                 port: int = 0) -> None:
        self.fake = fake
        self.scheduler = scheduler
        self._host, self._port = host, port
        self._listener: Optional[socket.socket] = None
        self.connections: List[_Connection] = []
        self._late: Dict[int, Tuple[_Connection, jsonrpc.RequestId, Binding]] = {}   # fake request id -> who asked
        self._stopping = False
        fake.events.connect(self._on_event)

    @property
    def address(self) -> Tuple[str, int]:
        assert self._listener is not None, "start() the server first"
        host, port = self._listener.getsockname()[:2]
        return host, port

    def start(self) -> "FakeStationServer":
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self._host, self._port))
        listener.listen()
        self._listener = listener
        threading.Thread(target=self._accept_loop, name="fake-station-accept", daemon=True).start()
        return self

    def stop(self) -> None:
        self._stopping = True
        if self._listener is not None:
            self._listener.close()
        for conn in list(self.connections):
            conn.close()

    def drop_connections(self) -> None:
        """Test knob: close every client connection, as when the station service goes away."""
        for conn in list(self.connections):
            conn.close()

    # ---- sockets (accept and reader threads) -------------------------------------------------------------

    def _accept_loop(self) -> None:
        assert self._listener is not None
        while not self._stopping:
            try:
                sock, _ = self._listener.accept()
            except OSError:
                return
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn = _Connection(sock)
            self.scheduler.later(0, lambda c=conn: self.connections.append(c))
            threading.Thread(target=self._read_loop, args=(conn,), name=f"fake-station-conn-{conn.number}",
                             daemon=True).start()

    def _read_loop(self, conn: _Connection) -> None:
        reader = FrameReader()
        try:
            while conn.open:
                data = conn.sock.recv(65536)
                if not data:
                    break
                for body in reader.feed(data):
                    self.scheduler.later(0, lambda b=body: self._handle(conn, b))
        except FrameError:
            pass   # an oversized frame: the stream can't be trusted any more, so the connection closes
        except OSError:
            pass
        conn.close()
        self.scheduler.later(0, lambda: self._release(conn))

    def _release(self, conn: _Connection) -> None:
        """A client went away: its watches end and its console sessions close (the API doc's session rule)."""
        if conn in self.connections:
            self.connections.remove(conn)
        for sub_id in sorted(conn.watches):
            self.fake.unwatch(sub_id)
        for session_id in sorted(conn.sessions):
            self.fake.console_close(session_id)
        conn.watches.clear()
        conn.sessions.clear()

    # ---- requests (scheduler thread) ----------------------------------------------------------------------

    def _handle(self, conn: _Connection, body: bytes) -> None:
        request_id: Optional[jsonrpc.RequestId] = None
        try:
            message = decode_body(body)
            if isinstance(message, dict) and isinstance(message.get("id"), (int, str)):
                request_id = message["id"]
            request = jsonrpc.read_request(message)
        except FrameError as exc:
            conn.send(jsonrpc.protocol_error_reply(None, jsonrpc.ProtocolError(jsonrpc.PARSE_ERROR, str(exc))))
            return
        except jsonrpc.ProtocolError as exc:
            conn.send(jsonrpc.protocol_error_reply(request_id, exc))
            return

        def answer(message: Dict[str, Any]) -> None:
            if not request.is_notification:
                conn.send(message)

        method = BY_WIRE_NAME.get(request.method)
        if method is None:
            answer(jsonrpc.error_reply(request.id, jsonrpc.error_object(
                ApiError(ErrorCode.UNKNOWN_METHOD, f"Unknown method {request.method}"))))
            return
        try:
            args = self._arguments(method, request.params)
            if request.method == "sys.subscribe":
                conn.topics = self._topics(args[0])
        except ApiError as exc:
            answer(jsonrpc.error_reply(request.id, jsonrpc.error_object(exc)))
            return
        try:
            call: Call = getattr(self.fake, method.attr)(*args)
        except ApiError as exc:
            answer(jsonrpc.error_reply(request.id, jsonrpc.error_object(exc)))
            return
        except Exception as exc:   # a bug in the fake: answer instead of leaving the client waiting
            answer(jsonrpc.error_reply(request.id, jsonrpc.error_object(
                ApiError(ErrorCode.INTERNAL, f"{type(exc).__name__}: {exc}"))))
            return
        late = False   # set once this call has been answered with a timeout

        def timed_out() -> None:
            nonlocal late
            if call.pending and not request.is_notification:
                late = True
                answer(jsonrpc.error_reply(request.id, jsonrpc.error_object(ApiError(
                    ErrorCode.TIMEOUT, f"{request.method} didn't finish within {request.timeout_ms} ms",
                    {"still_running": True, "request_id": request.id}))))

        deadline = self.scheduler.later(request.timeout_ms, timed_out) if request.timeout_ms else None

        def ok(result: Any) -> None:
            if deadline is not None:
                deadline.cancel()
            self._track(conn, method, args, result)
            if late and request.id is not None:
                self._send_event(conn, CallLate(request.id, True, self._result(method, result)))
            else:
                answer(jsonrpc.reply(request.id, self._result(method, result)))

        def failed(error: ApiError) -> None:
            if deadline is not None:
                deadline.cancel()
            if late and request.id is not None:
                self._send_event(conn, CallLate(request.id, False, error=error))
            else:
                answer(jsonrpc.error_reply(request.id, jsonrpc.error_object(
                    self._note_timeout(conn, request.id, method, error))))

        call.then(ok, failed)

    @staticmethod
    def _topics(topics: List[str]) -> Set[str]:
        unknown = sorted(set(topics) - set(TOPICS))
        if unknown:
            raise ApiError(ErrorCode.INVALID_PARAMS, f"Unknown topic {unknown[0]}; the topics are {', '.join(TOPICS)}",
                           {"param": "topics"})
        return set(topics)

    @staticmethod
    def _track(conn: _Connection, method: Binding, args: List[Any], result: Any) -> None:
        """Remembers what the client opened, so it can be ended when the client goes away."""
        wire = method.method.wire
        if wire == "registers.watch":
            conn.watches.add(result)
        elif wire == "registers.unwatch":
            conn.watches.discard(args[0])
        elif wire == "advanced.console.open":
            conn.sessions.add(result)
        elif wire == "advanced.console.close":
            conn.sessions.discard(args[0])

    @staticmethod
    def _arguments(method: Binding, params: Dict[str, Any]) -> List[Any]:
        """The call's arguments in the gateway method's order. The protocol's types check them first (unknown,
        missing, badly typed or out of range: invalid_params), as a real station does; then each is built as
        the app type the fake takes."""
        checked = check_params(method.method, params)
        args = []
        for param, (_, app_type) in zip(method.method.params, method.args):
            if param.wire not in params:
                args.append(checked[param.wire])   # its default
                continue
            try:
                args.append(decode(app_type, params[param.wire], param.wire))
            except CodecError as exc:
                raise ApiError(ErrorCode.INVALID_PARAMS, str(exc), {"param": exc.path or param.wire}) from None
        return args

    @staticmethod
    def _result(method: Binding, result: Any) -> Any:
        """A result in its wire shape: {} for Empty, {wrap: value}, or the model's fields (the register tree has a
        shape of its own)."""
        return wrap_result(method.method, None if method.result is None else to_wire(method.result, result))

    def _note_timeout(self, conn: _Connection, request_id: Optional[jsonrpc.RequestId], method: Binding,
                      error: ApiError) -> ApiError:
        """A timeout whose call keeps running: remember who asked, and report the JSON-RPC id, not the fake's."""
        fake_id = error.data.get("request_id")
        if error.code == ErrorCode.TIMEOUT and isinstance(fake_id, int) and request_id is not None:
            self._late[fake_id] = (conn, request_id, method)
            return ApiError(error.code, error.message, {**error.data, "request_id": request_id})
        return error

    # ---- events (scheduler thread) ------------------------------------------------------------------------

    def _on_event(self, event: Any) -> None:
        if isinstance(event, CallLate):
            asked = self._late.pop(event.request_id, None) if isinstance(event.request_id, int) else None
            if asked is None:
                return
            conn, request_id, method = asked
            result = self._result(method, event.result) if event.ok else None   # the reply's shape
            self._send_event(conn, CallLate(request_id, event.ok, result, event.error))
            return
        name = NAMES.get(type(event))
        topic = BY_EVENT[name].topic if name else None
        for conn in list(self.connections):
            if topic in conn.topics:
                self._send_event(conn, event)

    @staticmethod
    def _send_event(conn: _Connection, event: Any) -> None:
        try:
            name, data = encode_event(event)
        except KeyError:
            return   # an event type with no wire name
        conn.send(jsonrpc.notification(name, next(conn.seq), data))


def serve(host: str = "127.0.0.1", port: int = DEFAULT_PORT, scenario: str = "happy") -> Tuple[FakeStationServer,
                                                                                                 Scenario]:
    """Starts a fake station with a scenario applied, listening on host:port (0 picks a free port)."""
    scheduler = ThreadScheduler("fake-station").start()
    fake = scheduler.run(lambda: FakeStationGateway(scheduler))
    chosen = scheduler.run(lambda: apply_scenario(fake, scenario))
    return FakeStationServer(fake, scheduler, host, port).start(), chosen


def main() -> None:
    parser = argparse.ArgumentParser(description="The fake SiBench station over TCP (JSON-RPC 2.0)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--scenario", default="happy")
    args = parser.parse_args()
    server, _ = serve(args.host, args.port, args.scenario)
    host, port = server.address
    print(f"Fake station listening on {host}:{port} (scenario {args.scenario}); Ctrl+C stops it", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
