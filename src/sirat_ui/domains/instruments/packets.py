"""PacketService (req 26 BLE packet, req 27 GFSK packet): code generation only, no station calls.

The BLE settings persist in ~/.sirat/ble_packet.json; GFSK packets become gfsk_packet actions.
"""

from __future__ import annotations

from typing import Callable

from sirat_ui.core.instruments import ble_from_json, gfsk_op
from sirat_ui.core.observable import Event
from sirat_ui.domains.automation.recorder import ActionRecorder
from sirat_ui.models.actions import Action
from sirat_ui.models.instruments import BlePacket, GfskPacket
from sirat_ui.stores.json_store import JsonStore


class PacketService:
    def __init__(self, store: JsonStore, actions: ActionRecorder, siggen_id: Callable[[], str]) -> None:
        self._store = store
        self._actions = actions
        self._siggen_id = siggen_id
        self.ble = ble_from_json(store.load())
        self.changed = Event()

    def reload(self) -> None:
        self.ble = ble_from_json(self._store.load())
        self.changed.emit()

    def remember_ble(self, packet: BlePacket) -> None:
        self.ble = packet
        self._store.save(packet.to_json())

    @property
    def siggen_id(self) -> str:
        return self._siggen_id() or "siggen1"

    def add_gfsk_action(self, packet: GfskPacket) -> Action:
        name = f"gfsk_{packet.symbol_rate_kbps:g}k_{packet.frequency_mhz:g}".replace(".", "p")
        return self._actions.add(name, [gfsk_op(packet, self.siggen_id)], enabled=False)
