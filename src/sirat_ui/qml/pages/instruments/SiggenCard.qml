import QtQuick 2.15
import "../../theme"

SiggenCardForm {
    readonly property var vm: app.siggen

    status.text: vm.instrumentText
    status.found: vm.instrumentFound
    status.connected: vm.instrumentConnected
    status.onConnectRequested: vm.connectInstrument()
    typeField.text: vm.sgType
    typeField.onTextEdited: vm.setField("sgType", typeField.text)
    typeField.invalid: !!vm.errors.sgType
    waveformCombo.model: vm.waveforms
    waveformCombo.currentIndex: vm.waveformIndex
    waveformCombo.onActivated: vm.setWaveform(index)
    reloadButton.enabled: vm.instrumentConnected
    reloadButton.onClicked: vm.reloadWaveforms()
    waveformHint.text: vm.waveformMissing ? "Not loaded on the instrument" : ""
    freqField.text: vm.frequency
    freqField.onTextEdited: vm.setField("frequency", freqField.text)
    freqField.invalid: !!vm.errors.frequency
    powerField.text: vm.power
    powerField.onTextEdited: vm.setField("power", powerField.text)
    powerField.invalid: !!vm.errors.power
    overridesField.text: vm.overrides
    overridesField.onTextEdited: vm.setField("overrides", overridesField.text)
    overridesField.invalid: !!vm.errors.overrides
    errorLabel.text: vm.errorText
    applyButton.enabled: vm.canApply
    applyButton.busy: vm.busy
    applyButton.onClicked: vm.apply()
    loadButton.enabled: vm.canControl
    loadButton.onClicked: vm.loadFromInstrument()
    rfControl.enabled: vm.canControl
    rfControl.currentIndex: vm.rfState === "on" ? 1 : vm.rfState === "off" ? 0 : -1
    rfControl.onActivated: vm.setRf(index === 1)
    infiniteButton.enabled: vm.canControl
    infiniteButton.onClicked: vm.trigger("infinite")
    singleButton.enabled: vm.canControl
    singleButton.onClicked: vm.trigger("single")
    triggerLabel.text: vm.triggerText
    addButton.enabled: vm.errorText === ""
    addButton.onClicked: vm.addToActions()
    codeButton.enabled: vm.errorText === ""
    codeButton.onClicked: vm.showCode()
    statusLabel.text: vm.statusText
    statusLabel.color: vm.statusLevel === "ok" ? Theme.okFg : vm.statusLevel === "danger" ? Theme.dangerFg : Theme.textMuted
}
