"""Demo user data for the fake backend, written only into an empty demo home."""

from __future__ import annotations

from sirat_ui.stores.formats import write_data_logger, write_favorites, write_watch_list
from sirat_ui.stores.json_store import UserStores

DEMO_ACTIONS = {
    "lpmode_on": {"operations": [{"register": "BUFC.LPMODE", "value": 3}], "enabled": True},
    "ble_1m_rx_setup": {"enabled": True, "operations": [
        {"type": "rf_switch", "path": "RX_PATH", "dut_position": 1},
        {"type": "load_phy", "phy_name": "BLE_1M", "method_name": "load_ble_phy"},
        {"register": "MODEM.CTRL", "value": 0x00000431},
        {"register": "MODEM.CTRL", "field": "OPMODE", "value": 2},
    ]},
    "siggen_2440_0dbm": {"enabled": False, "operations": [
        {"type": "signal_generator", "sg_type": "PacketSrw", "input_config_name": "BLE_1Mbps_37byte",
         "frequency_mhz": 2440, "power_dbm": 0, "overrides": {},
         "code": "siggen.configure('PacketSrw', 'BLE_1Mbps_37byte', 2440e6, 0)\nsiggen.trigger('InfiniteTrigger')"},
    ]},
    "reconnect_rpc": {"enabled": True, "operations": [{"type": "dut_reconnect", "description": "Reconnect RPC"}]},
}

DEMO_SEQUENCES = {
    "ble_rx_bringup": {"action_names": ["reconnect_rpc", "ble_1m_rx_setup", "siggen_2440_0dbm"],
                       "description": "Reconnect, route RX, load BLE 1M and start the signal generator"},
    "lp_mode_check": {"action_names": ["lpmode_on"], "description": ""},
}

DEMO_FAVORITES = ["MODEM.CTRL", "CMU.CLKEN0", "SYNTH.FREQ", "BUFC.LPMODE"]

DEMO_FORMULAS = {
    "SYNTH.FREQ.FREQ": {"formula": "x / 1000", "unit": "MHz"},
    "AGC.RSSI.RSSI": {"formula": "(x ^ 0x8000) - 0x8000", "unit": "dBm"},
}

DEMO_NOTES = {"BUFC.LPMODE.LPENBYM33": "Set by sequencer on boot"}

DEMO_WATCH = ["MODEM.CTRL.OPMODE", "SYNTH.FREQ.FREQ", "AGC.RSSI.RSSI", "AGC.EN.EN", "RAC.STATUS.STATE",
              "FRC.STATUS.ACTIVE"]


def seed_demo_data(stores: UserStores) -> bool:
    """Seeds only when no store file exists yet, so it never overwrites real data."""
    if any(store.exists for store in stores.all()):
        return False
    stores.actions.save(DEMO_ACTIONS)
    stores.sequences.save(DEMO_SEQUENCES)
    stores.favorites.save(write_favorites(DEMO_FAVORITES))
    stores.formulas.save(DEMO_FORMULAS)
    stores.notes.save(DEMO_NOTES)
    stores.watch_list.save(write_watch_list(DEMO_WATCH, 1.0))
    stores.data_logger.save(write_data_logger(["SYNTH.FREQ.FREQ", "AGC.RSSI.RSSI"], 0.5))
    return True
