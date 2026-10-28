"""PhyService (req 23): load LPW (BLE / 802.15.4) and WiFi PHYs, and turn them into Actions."""

from __future__ import annotations

from typing import Any, Dict, List

from sirat_ui.core.observable import Event
from sirat_ui.core.wifi import WifiPhyConfig
from sirat_ui.core.actions import Action
from sirat_ui.domains.automation.actions import ActionService
from sirat_ui.domains.connection.service import ConnectionService
from sirat_ui.gateway.call import Call
from sirat_ui.gateway.models import LoadPhyResult, LpwPhy, WifiPhy
from sirat_ui.state.app_state import AppState

# PHY names offered in the LPW drop-down; any other name can be typed or taken from a file.
KNOWN_LPW_PHYS: List[str] = ["BLE_1M", "BLE_2M", "BLE_CODED_125K", "BLE_CODED_500K", "IEEE802154_2P4GHZ",
                             "IEEE802154_2P4GHZ_ANTDIV"]
WIFI_FAMILY = "EVEREST"  # req 23: "Load WiFi PHY... (enabled only for Everest family)"


def lpw_op(name: str) -> Dict[str, Any]:
    return {"type": "load_phy", "phy_name": name, "method_name": "reset_and_download_lpw_phy"}


def wifi_op(config: WifiPhyConfig) -> Dict[str, Any]:
    """Req 23 "Action Format"."""
    return {"type": "load_wifi_phy", "config": config.to_dict()}


class PhyService:
    def __init__(self, connection: ConnectionService, state: AppState, actions: ActionService) -> None:
        self._connection = connection
        self._state = state
        self._actions = actions
        self.loaded = Event()  # (LoadPhyResult)

    @property
    def can_load(self) -> bool:
        return self._state.can("dut.load_phy")

    @property
    def wifi_supported(self) -> bool:
        chip = self._state.chip
        return chip is not None and chip.family.upper() == WIFI_FAMILY

    @property
    def chip_family(self) -> str:
        chip = self._state.chip
        return chip.family.title() if chip else ""

    def load_lpw(self, name: str) -> Call[LoadPhyResult]:
        return self._connection.load_phy(self._state.position, LpwPhy(name)).then(self.loaded.emit)

    def load_wifi(self, config: WifiPhyConfig) -> Call[LoadPhyResult]:
        return self._connection.load_phy(self._state.position, WifiPhy(config)).then(self.loaded.emit)

    def add_lpw_action(self, name: str) -> Action:
        return self._actions.add(self._actions.unique_name(f"load_{name.lower()}"), [lpw_op(name)])

    def add_wifi_action(self, config: WifiPhyConfig) -> Action:
        name = f"wifi_{config.mode.lower()}_{config.standard.replace('802.', '')}_ch{config.channel}"
        return self._actions.add(self._actions.unique_name(name), [wifi_op(config)])
