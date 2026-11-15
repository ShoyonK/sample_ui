"""Length-prefixed frames: a 4-byte big-endian length, then a UTF-8 JSON body of at most 16 MB."""

from __future__ import annotations

import json
import struct
from typing import Any, List

MAX_FRAME = 16 * 1024 * 1024
_HEADER = struct.Struct(">I")


class FrameError(Exception):
    """A frame that can't be read: too big, or not JSON. The connection can't be trusted after it."""


def encode_frame(message: Any) -> bytes:
    """One message as a frame. Raises FrameError when the body is over MAX_FRAME."""
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_FRAME:
        raise FrameError(f"Message is {len(body)} bytes; the limit is {MAX_FRAME}")
    return _HEADER.pack(len(body)) + body


class FrameReader:
    """Collects bytes as they arrive and returns whole frames' bodies, however the bytes were split."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> List[bytes]:
        """Adds received bytes; returns the bodies of the frames now complete. Raises FrameError on an
        oversized frame (before reading its body)."""
        self._buffer += data
        bodies: List[bytes] = []
        while len(self._buffer) >= _HEADER.size:
            (length,) = _HEADER.unpack_from(self._buffer)
            if length > MAX_FRAME:
                raise FrameError(f"Frame of {length} bytes is over the {MAX_FRAME}-byte limit")
            end = _HEADER.size + length
            if len(self._buffer) < end:
                break
            bodies.append(bytes(self._buffer[_HEADER.size:end]))
            del self._buffer[:end]
        return bodies


def decode_body(body: bytes) -> Any:
    """A frame body as JSON. Raises FrameError when it isn't UTF-8 JSON."""
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise FrameError(f"Frame isn't JSON: {exc}") from None
