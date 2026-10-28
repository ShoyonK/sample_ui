"""MemoryService (req 19): read raw memory, write a byte/word/dword, remember the last address.

The previous block is kept so the viewer can mark what changed between reads. After a write inside the
shown block, the block is read again so the change is visible straight away.
"""

from __future__ import annotations

import base64
from typing import Optional, Tuple

from sirat_ui.core.observable import Event
from sirat_ui.domains.logs.service import LogService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.port import MemoryPort
from sirat_ui.models.station import MemoryBlock, MemoryWriteRes
from sirat_ui.shared.error_presenter import ErrorPresenter
from sirat_ui.state.station import StationState
from sirat_ui.stores.json_store import JsonStore

Block = Tuple[int, bytes]


class MemoryService:
    def __init__(self, gateway: MemoryPort, state: StationState, store: JsonStore, errors: ErrorPresenter,
                 log: LogService) -> None:
        self._gateway = gateway
        self._state = state
        self._store = store
        self._errors = errors
        self._log = log
        self.block: Optional[Block] = None
        self.previous: Optional[Block] = None
        self.requested: Tuple[int, int] = (0, 0)     # (address, size) the user asked for
        self.busy = False
        self.changed = Event()

    @property
    def last_address(self) -> str:
        return str(self._store.load().get("last_address") or "0x20000000")

    def read(self, address: int, size: int) -> Call[MemoryBlock]:
        self.busy = True
        self.changed.emit()

        def done(block: MemoryBlock) -> None:
            self.busy = False
            data = base64.b64decode(block.data)
            same_place = self.block is not None and self.block[0] == block.address
            self.previous = self.block if same_place else None
            self.block, self.requested = (block.address, data), (address, size)
            self._store.save({"last_address": f"0x{address:08X}"})   # req 19: saved on a successful read
            self.changed.emit()

        def failed(error: ApiError) -> None:
            self.busy = False
            self.changed.emit()
            self._errors.present(error, "Memory read")

        return self._gateway.memory_read(self._state.position, address, size).then(done, failed)

    def write(self, address: int, value: int, size: int) -> Call[MemoryWriteRes]:
        def done(res: MemoryWriteRes) -> None:
            digits = size * 2
            self._log.success(f"Wrote 0x{value:0{digits}X} to 0x{address:08X} "
                              f"(read back 0x{res.value_readback:0{digits}X})")
            if self.block is not None and self.block[0] <= address < self.block[0] + len(self.block[1]):
                self.read(*self.requested)

        return self._gateway.memory_write(self._state.position, address, value, size).then(
            done, lambda e: self._errors.present(e, "Memory write"))

    def reload(self) -> None:
        self.changed.emit()
