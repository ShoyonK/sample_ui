"""Instruments page, packet cards: BLE packet (req 26) and GFSK packet (req 27) code generation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core.instruments import ble_code, ble_problems, gfsk_code, gfsk_problems, parse_ble, PAYLOADS
from sirat_ui.domains.instruments.packets import PacketService
from sirat_ui.models.instruments import GfskPacket
from sirat_ui.shared.interactions import InteractionService
from sirat_ui.shared.qt import pyqtProperty
from sirat_ui.shared.viewmodel import BaseViewModel, qprop

BLE_FIELDS = ("accessAddress", "crcInit", "whitening", "preamble")
GFSK_FIELDS = ("rate", "deviation", "bt", "frequency", "power", "length")


class BlePacketViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: PacketService, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._interactions = interactions
        self._accessAddress = self._crcInit = self._whitening = self._preamble = ""
        self._errors = {}
        service.changed.connect(self._load)
        self._load()

    accessAddress = qprop(str, "_accessAddress", changed)
    crcInit = qprop(str, "_crcInit", changed)
    whitening = qprop(str, "_whitening", changed)
    preamble = qprop(str, "_preamble", changed)

    @pyqtProperty("QVariantMap", notify=changed)
    def errors(self) -> Dict[str, Any]:
        return dict(self._errors)

    @pyqtProperty(str, notify=changed)
    def errorText(self) -> str:  # noqa: N802
        return " · ".join(self._errors.values())

    @pyqtProperty(bool, notify=changed)
    def canGenerate(self) -> bool:  # noqa: N802
        return not self._errors

    @pyqtProperty(str, notify=changed)
    def syncWord(self) -> str:  # noqa: N802
        packet = self._packet()
        return f"0x{packet.sync_word:08X}" if packet else "—"

    def _packet(self):
        return parse_ble(self._accessAddress, self._crcInit, self._whitening, self._preamble)

    def _load(self) -> None:
        data = self._service.ble.to_json()
        self._accessAddress, self._crcInit = data["access_address"], data["crc_init"]
        self._whitening, self._preamble = str(data["whitening_init"]), data["preamble"]
        self._errors = {}
        self.changed.emit()

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name not in BLE_FIELDS:
            return
        setattr(self, "_" + name, value)
        self._errors = ble_problems(self._accessAddress, self._crcInit, self._whitening, self._preamble)
        packet = self._packet()
        if packet:
            self._service.remember_ble(packet)  # req 26 "Configuration persists across sessions"
        self.changed.emit()

    @pyqtSlot()
    def generateCode(self) -> None:  # noqa: N802
        packet = self._packet()
        if packet:
            self._interactions.show_code("BLE packet code", ble_code(packet))


class GfskPacketViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: PacketService, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._interactions = interactions
        d = GfskPacket()
        self._rate, self._deviation, self._bt = f"{d.symbol_rate_kbps:g}", f"{d.deviation_khz:g}", f"{d.bt:g}"
        self._frequency, self._power, self._length = f"{d.frequency_mhz:g}", f"{d.power_dbm:g}", str(d.payload_length)
        self._payload = d.payload
        self._errors = {}

    rate = qprop(str, "_rate", changed)
    deviation = qprop(str, "_deviation", changed)
    bt = qprop(str, "_bt", changed)
    frequency = qprop(str, "_frequency", changed)
    power = qprop(str, "_power", changed)
    length = qprop(str, "_length", changed)

    @pyqtProperty("QStringList", constant=True)
    def payloads(self) -> List[str]:
        return PAYLOADS

    @pyqtProperty(int, notify=changed)
    def payloadIndex(self) -> int:  # noqa: N802
        return PAYLOADS.index(self._payload)

    @pyqtProperty("QVariantMap", notify=changed)
    def errors(self) -> Dict[str, Any]:
        return dict(self._errors)

    @pyqtProperty(str, notify=changed)
    def errorText(self) -> str:  # noqa: N802
        return " · ".join(self._errors.values())

    @pyqtProperty(bool, notify=changed)
    def canGenerate(self) -> bool:  # noqa: N802
        return not self._errors

    @pyqtProperty(str, notify=changed)
    def modulationIndex(self) -> str:  # noqa: N802
        """h = 2 × deviation / symbol rate (0.5 for BLE 1M)."""
        try:
            return f"h = {2 * float(self._deviation) / float(self._rate):.3g}"
        except (ValueError, ZeroDivisionError):
            return "h = —"

    def _packet(self) -> Optional[GfskPacket]:
        if self._errors:
            return None
        return GfskPacket(float(self._rate), float(self._deviation), float(self._bt), float(self._frequency),
                          float(self._power), self._payload, int(self._length))

    @pyqtSlot(str, str)
    def setField(self, name: str, value: str) -> None:  # noqa: N802
        if name not in GFSK_FIELDS:
            return
        setattr(self, "_" + name, value)
        self._errors = gfsk_problems(self._rate, self._deviation, self._bt, self._frequency, self._power,
                                     self._length)
        self.changed.emit()

    @pyqtSlot(int)
    def setPayload(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(PAYLOADS):
            self._update(payload=PAYLOADS[index])

    @pyqtSlot()
    def generateCode(self) -> None:  # noqa: N802
        packet = self._packet()
        if packet:
            self._interactions.show_code("GFSK packet code", gfsk_code(packet, self._service.siggen_id))

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        packet = self._packet()
        if packet:
            action = self._service.add_gfsk_action(packet)
            self._interactions.toast("success", f"Added {action.name} to Actions")


__all__: List[str] = ["BlePacketViewModel", "GfskPacketViewModel"]
