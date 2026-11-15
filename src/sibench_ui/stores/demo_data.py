"""Demo user data for the fake backend, written only into an empty demo home (and an empty dumps folder)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from sibench_ui.core.dumps import write_csv
from sibench_ui.models.dumps import RegisterDump
from sibench_ui.models.registers import PeripheralDef
from sibench_ui.stores.formats import write_data_logger, write_favorites, write_watch_list
from sibench_ui.stores.json_store import UserStores

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

# The radio's state machine, its receive chain and the buffer behind it; the fake moves the starred ones on every
# watch tick (gateway/fake/register_memory.py advance_live), so the list shows live values
DEMO_WATCH = [
    "RAC.STATUS.STATE",                 # * OFF, RXWARM, RXSEARCH, RXFRAME
    "MODEM.CTRL.OPMODE", "MODEM.STATUS.DEMODSTATE",   # * demodulator state follows the radio state
    "FRC.STATUS.ACTIVE",                # * active while a frame is received
    "SYNTH.FREQ.FREQ",                  # * drifts a few counts around 2.44 GHz
    "SYNTH.CHCTRL.CHNO",
    "AGC.RSSI.RSSI",                    # * -86..-68 dBm
    "AGC.CTRL0.PWRTARGET", "AGC.CTRL0.MODE", "AGC.EN.EN",
    "BUFC.BUF0_STATUS.BYTES",           # * bytes waiting in the RX buffer
    "BUFC.BUF0_WRITEOFFSET.WRITEOFFSET", "BUFC.BUF0_READOFFSET.READOFFSET",   # * advance as frames arrive
    "BUFC.LPMODE.LPENBYSEQ", "CMU.CLKEN0.RADIOAES", "GPIO.PA_DOUT.DOUT",
]

# Dumps the Diffs page starts with: three snapshots of one bring-up, so comparing neighbours shows a clear diff.
# Each holds every register a dump would read (readable, not read-sensitive), at its reset value except for these
# changes.
_AFTER_BOOT = {
    "MODEM.CTRL": 0x0000,          # OPMODE IDLE
    "RAC.STATUS": 0x0, "RAC.CTRL": 0x1,                       # radio OFF, forced off
    "FRC.STATUS": 0x0,
    "SYNTH.FREQ": 2_402_000,       # channel 0
    "CMU.CLKEN0": 0x003,           # only LDMA clocks: RADIOAES and the timers off
    "AGC.CTRL0": 0x0000, "AGC.RSSI": 0xFF80,
}
_BLE_RX = {
    "MODEM.CTRL": 0x0206,          # OPMODE RX, CODING 1, DEMODSEL 2
    "RAC.STATUS": 0x3, "RAC.CTRL": 0x0,                       # RXSEARCH, no longer forced off
    "FRC.STATUS": 0x1,
    "SYNTH.FREQ": 2_440_000, "SYNTH.CHCTRL": 19,              # channel 19
    "CMU.CLKEN0": 0xF07,           # RADIOAES and TIMER0..3 on
    "AGC.CTRL0": 0x013C,           # MODE LOCKPREDET, PWRTARGET 0x3C
    "AGC.RSSI": 0xFFB4,            # -76 dBm
    "BUFC.LPMODE": 0x3, "BUFC.BUF0_CTRL": 0x2,                # both low-power enables; 256-byte buffer
    "BUFC.BUF0_ADDR": 0x20001000,
    "GPIO.PA_MODEL": 0x41, "GPIO.PA_DOUT": 0x0010,            # PA0 input, PA1 push-pull; PA4 high
}
_BLE_RX_40C = {**_BLE_RX,
               "AGC.CTRL0": 0x0142,      # PWRTARGET 0x3C -> 0x42 at temperature
               "AGC.RSSI": 0xFFAE,       # -82 dBm
               "SYNTH.FREQ": 2_440_003}
DEMO_DUMPS: Tuple[Tuple[str, str, Dict[str, int]], ...] = (
    ("after_boot", "09:05:12", _AFTER_BOOT),
    ("ble_1m_rx", "09:41:37", _BLE_RX),
    ("ble_1m_rx_40C", "10:18:02", _BLE_RX_40C),
)


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


def seed_demo_dumps(directory: Path, peripherals: Sequence[PeripheralDef], day: dt.date) -> List[Path]:
    """Writes DEMO_DUMPS as dump CSVs dated `day`, only into a folder with no dumps yet. Returns what it wrote."""
    if directory.exists() and any(directory.glob("*.csv")):
        return []
    registers = [r for p in peripherals for r in p.registers if r.access.readable and not r.read_sensitive]
    written = []
    for name, time, changes in DEMO_DUMPS:
        values = {r.full_name: changes.get(r.full_name, r.reset) for r in registers}
        dump = RegisterDump(name, dt.datetime.combine(day, dt.time.fromisoformat(time)), values=values,
                            addresses={r.full_name: r.address for r in registers})
        written.append(write_csv(directory, dump))
    return written
