"""Radio and PHY page: Load LPW PHY and WiFi PHY (req 23), PRS signal routing (req 24)."""

import pytest

from sirat_ui.core import wifi
from sirat_ui.core.prs import CONSTRAINT_TEXT, channel_problem, removal_ops
from sirat_ui.core.registers import ChipInfo
from sirat_ui.core.wifi import WifiPhyConfig, WifiSettings, packet_layout
from sirat_ui.gateway.models import PrsRoute
from support import Harness

EVEREST = ChipInfo("SIWG917M", "B0", "EVEREST")


@pytest.fixture
def everest(qapp, tmp_path):
    return Harness(tmp_path, chip=EVEREST)


def last_action(h):
    return h.services.actions.actions[next(reversed(h.services.actions.actions))]


# ---- Load LPW PHY ---------------------------------------------------------------------------------------

@pytest.mark.req("23.lpw")
def test_load_lpw_phy_then_offer_add_to_actions(harness):
    vm = harness.shell.lpwPhy
    vm.setPhyName("BLE_2M")
    harness.ix.answer_next(True)  # "Add to Actions" in the success dialog
    vm.load()
    harness.scheduler.run_pending()
    assert harness.fake.facts[1].phy == "BLE_2M" and vm.currentPhy == "BLE_2M"
    assert harness.ix.confirms[-1].title == "Loaded PHY BLE_2M"
    assert "reset_and_download_lpw_phy" in harness.ix.confirms[-1].message
    assert last_action(harness).operations == [
        {"type": "load_phy", "phy_name": "BLE_2M", "method_name": "reset_and_download_lpw_phy"}]


def test_lpw_phy_name_can_come_from_a_file(harness, tmp_path):
    harness.ix.answer_open(str(tmp_path / "IEEE802154_2P4GHZ_CUSTOM.cfg"))
    harness.shell.lpwPhy.browse()
    assert harness.shell.lpwPhy.phyName == "IEEE802154_2P4GHZ_CUSTOM"


def test_lpw_load_needs_a_connection(qapp, tmp_path):
    h = Harness(tmp_path, connect=False)
    assert h.shell.lpwPhy.canLoad is False


# ---- WiFi PHY ---------------------------------------------------------------------------------------------

@pytest.mark.req("23.wifi")
def test_wifi_is_only_for_everest_chips(harness):
    vm = harness.shell.wifiPhy
    assert vm.available is False and vm.unavailableText == "WiFi PHYs are for Everest-family chips. This DUT is Lion."
    vm.apply()
    assert harness.ix.toasts[-1] == ("error", vm.unavailableText)
    assert harness.shell.recovery.wifiAvailable is False


@pytest.mark.req("23.wifi")
def test_apply_wifi_rx_shows_the_success_dialog(everest):
    vm = everest.shell.wifiPhy
    assert vm.available and vm.mode == "RX" and vm.standard == "802.11g" and vm.channel == "6"
    vm.apply()
    everest.scheduler.run_pending()
    assert vm.resultOpen and vm.resultFunction == "load_wifi_phy(test_obj, config)"
    rows = {r["key"]: r["value"] for r in vm.resultRows}
    assert rows == {"PHY": "WIFI_2p4G", "Mode": "RX", "Standard": "802.11g", "Channel": "6", "Power mode": "HP",
                    "Rate": "24 Mb/s"}
    assert ("WIFI_STANDARD", "802.11g") in [(r["key"], r["value"]) for r in vm.overrideRows]
    assert everest.fake.facts[1].phy == "WIFI_2p4G"
    assert everest.shell.recovery.wifiAvailable is True


def test_wifi_tx_ax_on_5ghz_uses_the_power_mode_in_the_phy_name(everest):
    vm = everest.shell.wifiPhy
    vm.setMode("TX")
    vm.setStandard("802.11ax")
    vm.setChannel("36")
    vm.setPowerMode("MP")
    vm.setAdvancedEnabled(True)
    vm.setBandwidth("BW_80MHz")
    vm.setPktLength("4000")
    assert vm.phyName == "PHY_WIFI_5G_MP" and "MP" in vm.powerModes
    vm.addToActions()
    op = last_action(everest).operations[0]
    assert op["type"] == "load_wifi_phy"
    assert op["config"]["tx_params"] == {"pkt_length": 4000, "num_pkts": 0, "transmit_mode": "BURST",
                                         "aggr_enable": True}
    assert op["config"]["advanced"]["bandwidth"] == "BW_80MHz" and op["config"]["rate"] == "7"


def test_changing_standard_keeps_choices_valid(everest):
    vm = everest.shell.wifiPhy
    vm.setStandard("802.11a")  # 5 GHz only: channel 6 isn't allowed
    assert vm.channel == "36" and vm.rate == "24" and "6" not in vm.channelOptions
    vm.setStandard("802.11b")
    assert vm.channel == "6" and vm.rateOptions == ["1", "2", "5.5", "11"] and vm.rate == "11"
    assert vm.advancedAvailable is False


def test_bad_tx_numbers_block_apply(everest):
    vm = everest.shell.wifiPhy
    vm.setMode("TX")
    vm.setPktLength("abc")
    assert vm.problems == "Packet length must be a whole number" and vm.canApply is False
    vm.setPktLength("70000")
    assert "1 to 65535" in vm.problems
    vm.setPktLength("1500")
    assert vm.problems == "" and vm.canApply is True


def test_packet_visualizer_follows_the_standard_and_mode():
    names = [s.name for s in packet_layout(WifiSettings(standard="802.11ax", channel=36)).segments]
    assert names[:4] == ["L-STF", "L-LTF", "L-SIG", "RL-SIG"] and names[-1] == "PE"
    tx = packet_layout(WifiSettings(mode="TX", standard="802.11g", rate="54", pkt_length=1500))
    data = next(s for s in tx.segments if s.kind == "data")
    assert data.us == pytest.approx(1500 * 8 / 54, abs=0.1) and "54 Mb/s" in tx.caption
    assert next(s for s in packet_layout(WifiSettings()).segments if s.kind == "data").us is None  # RX


def test_wifi_config_round_trips_through_the_action_format():
    config = WifiSettings(mode="TX", standard="802.11be", channel=149, power_mode="LP", rate="MCS13",
                          advanced_enabled=True).normalized().config()
    assert WifiPhyConfig.from_dict(config.to_dict()) == config
    assert config.phy_name == "PHY_WIFI_5G_LP" and wifi.phy_name("802.11n", 11, "HP") == "WIFI_2p4G"


# ---- PRS routing ------------------------------------------------------------------------------------------

@pytest.mark.req("24.signals")
def test_signals_come_from_the_chip_family_with_categories(harness):
    vm = harness.shell.prs
    assert vm.sourceText == "Lion · dut_control_rta.series_six_lpw.lion.controls.pti_prs_module"
    assert "FRAMEDET  (MODEM)" in vm.signalLabels and "DISABLE" not in vm.signalLabels


@pytest.mark.req("24.validate")
def test_port_channel_rule_is_checked_on_apply(harness):
    vm = harness.shell.prs
    vm.setPin(vm.pins.index("PC2"))
    vm.setChannel(3)
    assert vm.invalid and "channel 3 won't work" in vm.hint
    vm.apply()
    assert (harness.ix.alerts[-1].title, harness.ix.alerts[-1].message) == (
        "Invalid Port/Channel Combination", CONSTRAINT_TEXT)
    assert harness.fake.prs_routes[1] == {}


@pytest.mark.req("24.apply")
def test_apply_lists_the_route_and_replaces_one_on_the_same_channel(harness):
    vm = harness.shell.prs
    vm.setSignal([s.split()[0] for s in vm.signalLabels].index("FRAMEDET"))
    vm.setPin(vm.pins.index("PA0"))
    vm.setChannel(0)
    vm.apply()
    assert harness.ix.toasts[-1] == ("success", "Successfully routed FRAMEDET to PA0 via PRS channel 0")
    vm.setSignal([s.split()[0] for s in vm.signalLabels].index("PREDET"))
    vm.setPin(vm.pins.index("PA1"))
    vm.apply()
    assert vm.routes.items == [{"signal": "PREDET", "pin": "PA1", "channel": 0}]
    assert harness.fake.prs_routes[1] == {0: PrsRoute("PREDET", "PA1", 0)}


@pytest.mark.req("24.remove")
def test_remove_disables_the_channel_and_records_the_register_writes(harness):
    vm = harness.shell.prs
    vm.setPin(vm.pins.index("PB3"))
    vm.setChannel(4)
    vm.apply()
    vm.remove(0)
    assert vm.routes.count == 0 and harness.fake.prs_routes[1] == {}
    targets = [e.target for e in harness.services.history.entries[-6:]]
    assert targets == ["PRS.ASYNC_CH4_CTRL.SOURCESEL", "PRS.ASYNC_CH4_CTRL.SIGSEL", "GPIO.PRS0_ROUTEEN.ASYNCH4PEN",
                       "GPIO.PRS0_ASYNCH4ROUTE.PORT", "GPIO.PRS0_ASYNCH4ROUTE.PIN", "GPIO.PORTB_MODEL.MODE3"]


def test_routes_are_cleared_when_the_dut_disconnects(harness):
    vm = harness.shell.prs
    vm.apply()
    assert vm.routes.count == 1
    harness.fake.drop_dut(1, "power cycle")
    assert vm.routes.count == 0


def test_add_route_to_actions(harness):
    vm = harness.shell.prs
    vm.setPin(vm.pins.index("PD7"))
    vm.setChannel(11)
    vm.addToActions()
    op = last_action(harness).operations[0]
    assert op == {"type": "prs_route", "signal": vm.current_route().signal, "pin": "PD7", "channel": 11}


def test_prs_rules_on_their_own():
    assert channel_problem("PA5", 5) is None and channel_problem("PD0", 6) is None
    assert channel_problem("PB0", 6) == CONSTRAINT_TEXT
    assert removal_ops("PC2", 7)[-1] == ("GPIO.PORTC_MODEL", "MODE2", 0)
