"""Advanced page, Memory tab (req 19): address / size / format, the hex dump, and a confirmed write."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.memory import (FORMATS, MAX_READ, WRITE_SIZES, address_problem, dump_text, parse_number, rows,
                                  size_problem, write_problem)
from sirat_ui.domains.advanced.memory import MemoryService
from sirat_ui.models.dialogs import ConfirmRequest
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, DictListModel, clock_text, copy_to_clipboard, qprop
from sirat_ui.state.station import StationState

FIELDS = ("address", "size", "writeAddress", "writeValue")


class MemoryViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: MemoryService, state: StationState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._interactions = interactions
        self._address = service.last_address
        self._size = "256"
        self._format = 0
        self._writeAddress = service.last_address
        self._writeValue = ""
        self._writeSize = 2     # DWord (req 19 default)
        self._readAt = 0.0
        self._rows = DictListModel(["address", "cells", "ascii"], self)
        service.changed.connect(self._rebuild)
        state.changed.connect(self.changed.emit)

    @pyqtProperty(QObject, constant=True)
    def rows(self) -> QObject:
        return self._rows

    address = qprop(str, "_address", changed)
    size = qprop(str, "_size", changed)

    @pyqtProperty("QStringList", constant=True)
    def formats(self) -> List[str]:
        return list(FORMATS)

    formatIndex = qprop(int, "_format", changed)
    writeAddress = qprop(str, "_writeAddress", changed)
    writeValue = qprop(str, "_writeValue", changed)

    @pyqtProperty("QStringList", constant=True)
    def writeSizes(self) -> List[str]:  # noqa: N802
        return [n for n, _ in WRITE_SIZES]

    writeSizeIndex = qprop(int, "_writeSize", changed)

    @pyqtProperty(bool, notify=changed)
    def busy(self) -> bool:
        return self._service.busy

    @pyqtProperty(bool, notify=changed)
    def hasData(self) -> bool:  # noqa: N802
        return self._service.block is not None

    @pyqtProperty(bool, notify=changed)
    def connected(self) -> bool:
        return self._state.connected

    @pyqtProperty(int, constant=True)
    def maxRead(self) -> int:  # noqa: N802
        return MAX_READ

    @pyqtProperty("QVariantMap", notify=changed)
    def errors(self) -> Dict[str, str]:
        out = {"address": address_problem(self._address), "size": size_problem(self._size)}
        if self._writeValue or self._writeAddress != self._address:
            out["write"] = write_problem(self._writeAddress, self._writeValue, self._write_bytes())
        return {k: v for k, v in out.items() if v}

    def _write_bytes(self) -> int:
        return WRITE_SIZES[self._writeSize][1]

    @pyqtProperty(bool, notify=changed)
    def canRead(self) -> bool:  # noqa: N802
        e = self.errors
        return self._state.connected and not self._service.busy and "address" not in e and "size" not in e

    @pyqtProperty(bool, notify=changed)
    def canWrite(self) -> bool:  # noqa: N802
        return self._state.connected and bool(self._writeValue) and not write_problem(
            self._writeAddress, self._writeValue, self._write_bytes())

    @pyqtProperty(str, notify=changed)
    def headerText(self) -> str:  # noqa: N802
        block = self._service.block
        if block is None:
            return ""
        start, data = block
        asked, _ = self._service.requested
        aligned = f" (aligned from 0x{asked:08X})" if asked != start else ""
        changed = sum(c for r in self._rows.items for c in (cell["c"] for cell in r["cells"]))
        delta = f" · {changed} changed since the last read" if self._service.previous is not None else ""
        return f"0x{start:08X}{aligned} · {len(data)} bytes · read at {clock_text(self._readAt)}{delta}"

    @pyqtProperty(str, notify=changed)
    def emptyText(self) -> str:  # noqa: N802
        if not self._state.connected:
            return "Connect a DUT to read its memory"
        return "Enter an address and press Read. RAM starts at 0x20000000, flash at 0x08000000."

    def _rebuild(self) -> None:
        block = self._service.block
        if block is not None and not self._service.busy:
            self._readAt = time.time()
        fmt = FORMATS[self._format]
        out = []
        if block is not None:
            for row in rows(block[0], block[1], fmt, self._service.previous):
                out.append({"address": f"0x{row.address:08X}", "ascii": row.ascii,
                            "cells": [{"t": text, "c": changed} for text, changed in row.cells]})
        self._rows.set_items(out)
        self.changed.emit()

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name in FIELDS:
            self._update(**{name: value})

    @pyqtSlot(int)
    def setFormat(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(FORMATS) and index != self._format:
            self._format = index
            self._rebuild()

    @pyqtSlot(int)
    def setWriteSize(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(WRITE_SIZES):
            self._update(writeSize=index)

    @pyqtSlot()
    def read(self) -> None:
        if self.canRead:
            self._service.read(parse_number(self._address) or 0, parse_number(self._size) or 1)

    @pyqtSlot(int)
    def useRowAddress(self, row: int) -> None:  # noqa: N802
        """Clicking a row's address puts it in the write address."""
        item = self._rows.get(row)
        if item:
            self._update(writeAddress=item["address"])

    @pyqtSlot()
    def write(self) -> None:
        if not self.canWrite:
            return
        address, value = parse_number(self._writeAddress) or 0, parse_number(self._writeValue) or 0
        name, size = WRITE_SIZES[self._writeSize]
        digits = size * 2
        request = ConfirmRequest("Confirm memory write", f"Write 0x{value:0{digits}X} to address 0x{address:08X}?",
                                 [("Size", f"{name} ({size} byte{'s' if size > 1 else ''})"),
                                  ("DUT", str(self._state.position))],
                                 warning="Raw memory writes bypass the register access policy.",
                                 confirm_text="Write", tone="danger")
        self._interactions.confirm(request).then(
            lambda a: self._service.write(address, value, size) if a.accepted else None)

    @pyqtSlot()
    def copyDump(self) -> None:  # noqa: N802
        block = self._service.block
        if block is not None:
            copy_to_clipboard(dump_text(block[0], block[1], FORMATS[self._format]))
            self._interactions.toast("success", "Copied the dump")
