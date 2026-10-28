"""Radio and PHY page, PHY cards (req 23): Load LPW PHY, and the WiFi PHY configuration with its live packet
visualizer and success dialog.

QML changes settings only through the typed slots below; WifiSettings.normalized() keeps every combination
valid, so the drop-downs never offer a choice the current standard or channel doesn't allow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from sirat_ui.core import wifi
from sirat_ui.core.wifi import WifiSettings
from sirat_ui.domains.radio.phy import KNOWN_LPW_PHYS, PhyService
from sirat_ui.gateway.errors import ApiError
from sirat_ui.gateway.models import LoadPhyResult
from sirat_ui.shared.interactions import ConfirmRequest, InteractionService
from sirat_ui.shared.viewmodel import BaseViewModel, qprop
from sirat_ui.state.app_state import AppState
from sirat_ui.shared.qt import pyqtProperty

PHY_FILE_FILTER = "PHY files (*.cfg *.json *.py);;All files (*)"


class LpwPhyViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: PhyService, state: AppState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._interactions = interactions
        self._phy_name = KNOWN_LPW_PHYS[0]
        self._busy = False
        self._current_phy = ""
        self._can_load = False
        state.changed.connect(self._refresh)
        self._refresh()

    phyName = qprop(str, "_phy_name", changed)
    busy = qprop(bool, "_busy", changed)
    currentPhy = qprop(str, "_current_phy", changed)
    canLoad = qprop(bool, "_can_load", changed)
    knownPhys = pyqtProperty("QStringList", lambda self: KNOWN_LPW_PHYS, constant=True)

    def _refresh(self, *_: object) -> None:
        self._update(current_phy=self._state.facts.phy or "", can_load=self._service.can_load and not self._busy)

    @pyqtSlot(str)
    def setPhyName(self, name: str) -> None:  # noqa: N802
        self._update(phy_name=name.strip())

    @pyqtSlot()
    def browse(self) -> None:
        def chosen(path: Optional[str]) -> None:
            if path:
                self._update(phy_name=Path(path).stem)

        self._interactions.choose_open_file("Select a PHY file", PHY_FILE_FILTER).then(chosen)

    @pyqtSlot()
    def load(self) -> None:
        name = self._phy_name
        if not name:
            self._interactions.toast("error", "Enter a PHY name or pick a PHY file")
            return
        self._update(busy=True)
        self._refresh()

        def loaded(result: LoadPhyResult) -> None:
            self._update(busy=False)
            self._refresh()
            request = ConfirmRequest(f"Loaded PHY {result.name}", f"{result.function}(dut, '{result.name}') finished. "
                                     "Add it to Actions to load it again in one click?",
                                     confirm_text="Add to Actions", tone="info")
            self._interactions.confirm(request).then(lambda a: self._add(result.name) if a.accepted else None)

        def failed(_: ApiError) -> None:
            self._update(busy=False)
            self._refresh()

        self._service.load_lpw(name).then(loaded, failed)

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if self._phy_name:
            self._add(self._phy_name)

    def _add(self, name: str) -> None:
        action = self._service.add_lpw_action(name)
        self._interactions.toast("success", f"Added {action.name} to Actions")


class WifiPhyViewModel(BaseViewModel):
    changed = pyqtSignal()

    def __init__(self, service: PhyService, state: AppState, interactions: InteractionService,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._state = state
        self._interactions = interactions
        self._s = WifiSettings()
        self._input_errors: Dict[str, str] = {}
        self._busy = False
        self._result_open = False
        self._result_rows: List[Dict[str, str]] = []
        self._override_rows: List[Dict[str, str]] = []
        self._result_function = ""
        state.changed.connect(lambda *_: self.changed.emit())

    # ---- what QML shows ------------------------------------------------------------------------------

    available = pyqtProperty(bool, lambda self: self._service.wifi_supported, notify=changed)
    mode = pyqtProperty(str, lambda self: self._s.mode, notify=changed)
    standard = pyqtProperty(str, lambda self: self._s.standard, notify=changed)
    channel = pyqtProperty(str, lambda self: str(self._s.channel), notify=changed)
    powerMode = pyqtProperty(str, lambda self: self._s.power_mode, notify=changed)
    rate = pyqtProperty(str, lambda self: self._s.rate, notify=changed)
    pktLength = pyqtProperty(str, lambda self: str(self._s.pkt_length), notify=changed)
    numPkts = pyqtProperty(str, lambda self: str(self._s.num_pkts), notify=changed)
    transmitMode = pyqtProperty(str, lambda self: self._s.transmit_mode, notify=changed)
    aggrEnable = pyqtProperty(bool, lambda self: self._s.aggr_enable, notify=changed)
    advancedAvailable = pyqtProperty(bool, lambda self: wifi.is_advanced(self._s.standard), notify=changed)
    advancedEnabled = pyqtProperty(bool, lambda self: self._s.advanced_enabled, notify=changed)
    ppduType = pyqtProperty(str, lambda self: self._s.ppdu_type, notify=changed)
    giLtf = pyqtProperty(str, lambda self: self._s.gi_ltf, notify=changed)
    dcm = pyqtProperty(bool, lambda self: self._s.dcm, notify=changed)
    bandwidth = pyqtProperty(str, lambda self: self._s.bandwidth, notify=changed)
    phyName = pyqtProperty(str, lambda self: self._s.config().phy_name, notify=changed)
    busy = qprop(bool, "_busy", changed)

    standards = pyqtProperty("QStringList", lambda self: wifi.STANDARDS, constant=True)
    transmitModes = pyqtProperty("QStringList", lambda self: wifi.TRANSMIT_MODES, constant=True)
    giLtfOptions = pyqtProperty("QStringList", lambda self: wifi.GI_LTF, constant=True)
    channelOptions = pyqtProperty("QStringList", lambda self: [str(c) for c in wifi.channels(self._s.standard)],
                                  notify=changed)
    powerModes = pyqtProperty("QStringList", lambda self: wifi.power_modes(self._s.standard), notify=changed)
    rateOptions = pyqtProperty("QStringList", lambda self: wifi.rates(self._s.standard), notify=changed)
    ppduTypes = pyqtProperty("QStringList", lambda self: wifi.PPDU_TYPES.get(self._s.standard, []), notify=changed)
    bandwidths = pyqtProperty("QStringList", lambda self: wifi.bandwidths(self._s.channel), notify=changed)

    @pyqtProperty(str, notify=changed)
    def unavailableText(self) -> str:  # noqa: N802
        family = self._service.chip_family
        if not family:
            return "Connect an Everest-family DUT to load WiFi PHYs."
        return f"WiFi PHYs are for Everest-family chips. This DUT is {family}."

    @pyqtProperty(str, notify=changed)
    def problems(self) -> str:
        return " · ".join(list(self._input_errors.values()) + self._s.problems())

    @pyqtProperty(bool, notify=changed)
    def canApply(self) -> bool:  # noqa: N802
        return self.available and self._service.can_load and not self._busy and not self.problems

    @pyqtProperty("QVariantList", notify=changed)
    def segments(self) -> List[Dict[str, Any]]:
        return [{"name": seg.name, "kind": seg.kind,
                 "label": "" if seg.us is None else f"{seg.us:g} µs", "us": seg.us or 0.0}
                for seg in wifi.packet_layout(self._s).segments]

    @pyqtProperty(str, notify=changed)
    def caption(self) -> str:
        return wifi.packet_layout(self._s).caption

    resultOpen = qprop(bool, "_result_open", changed)
    resultRows = qprop("QVariantList", "_result_rows", changed)
    overrideRows = qprop("QVariantList", "_override_rows", changed)
    resultFunction = qprop(str, "_result_function", changed)

    # ---- setters ---------------------------------------------------------------------------------------

    def _set(self, **changes: Any) -> None:
        values = dict(self._s.__dict__, **changes)
        self._s = WifiSettings(**values).normalized()
        self.changed.emit()

    @pyqtSlot(str)
    def setMode(self, mode: str) -> None:  # noqa: N802
        if mode in ("RX", "TX"):
            self._set(mode=mode)

    @pyqtSlot(str)
    def setStandard(self, standard: str) -> None:  # noqa: N802
        if standard in wifi.STANDARDS:
            self._set(standard=standard)

    @pyqtSlot(str)
    def setChannel(self, channel: str) -> None:  # noqa: N802
        if channel.isdigit() and int(channel) in wifi.channels(self._s.standard):
            self._set(channel=int(channel))

    @pyqtSlot(str)
    def setPowerMode(self, power_mode: str) -> None:  # noqa: N802
        self._set(power_mode=power_mode)

    @pyqtSlot(str)
    def setRate(self, rate: str) -> None:  # noqa: N802
        self._set(rate=rate)

    @pyqtSlot(str)
    def setPktLength(self, text: str) -> None:  # noqa: N802
        self._set_number("pkt_length", "Packet length", text)

    @pyqtSlot(str)
    def setNumPkts(self, text: str) -> None:  # noqa: N802
        self._set_number("num_pkts", "Number of packets", text)

    def _set_number(self, key: str, label: str, text: str) -> None:
        text = text.strip()
        if text.isdigit():
            self._input_errors.pop(key, None)
            self._set(**{key: int(text)})
        else:
            self._input_errors[key] = f"{label} must be a whole number"
            self.changed.emit()

    @pyqtSlot(str)
    def setTransmitMode(self, mode: str) -> None:  # noqa: N802
        if mode in wifi.TRANSMIT_MODES:
            self._set(transmit_mode=mode)

    @pyqtSlot(bool)
    def setAggrEnable(self, on: bool) -> None:  # noqa: N802
        self._set(aggr_enable=on)

    @pyqtSlot(bool)
    def setAdvancedEnabled(self, on: bool) -> None:  # noqa: N802
        self._set(advanced_enabled=on)

    @pyqtSlot(str)
    def setPpduType(self, ppdu: str) -> None:  # noqa: N802
        self._set(ppdu_type=ppdu)

    @pyqtSlot(str)
    def setGiLtf(self, gi_ltf: str) -> None:  # noqa: N802
        if gi_ltf in wifi.GI_LTF:
            self._set(gi_ltf=gi_ltf)

    @pyqtSlot(bool)
    def setDcm(self, on: bool) -> None:  # noqa: N802
        self._set(dcm=on)

    @pyqtSlot(str)
    def setBandwidth(self, bandwidth: str) -> None:  # noqa: N802
        self._set(bandwidth=bandwidth)

    # ---- apply / add to actions ------------------------------------------------------------------------

    @pyqtSlot()
    def apply(self) -> None:
        if not self.canApply:
            reason = self.problems or (self.unavailableText if not self.available else "")
            if reason:
                self._interactions.toast("error", reason)
            return
        config = self._s.config()
        self._update(busy=True)

        def loaded(result: LoadPhyResult) -> None:
            rows = [("PHY", result.name), ("Mode", config.mode), ("Standard", config.standard),
                    ("Channel", str(config.channel)), ("Power mode", config.power_mode),
                    ("Rate", self._s.rate if self._s.rate.startswith("MCS") else f"{config.rate} Mb/s")]
            self._update(busy=False, result_open=True, result_function=f"{result.function}(test_obj, config)",
                         result_rows=[{"key": k, "value": v} for k, v in rows],
                         override_rows=[{"key": k, "value": v} for k, v in result.overrides])

        self._service.load_wifi(config).then(loaded, lambda _: self._update(busy=False))

    @pyqtSlot()
    def addToActions(self) -> None:  # noqa: N802
        if self.problems:
            self._interactions.toast("error", self.problems)
            return
        action = self._service.add_wifi_action(self._s.config())
        self._interactions.toast("success", f"Added {action.name} to Actions")

    @pyqtSlot()
    def closeResult(self) -> None:  # noqa: N802
        self._update(result_open=False)

    def settings(self) -> WifiSettings:
        """For tests and the screenshot script."""
        return self._s
