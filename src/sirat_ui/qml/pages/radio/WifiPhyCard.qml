import QtQuick 2.15

WifiPhyCardForm {
    readonly property var vm: app.wifiPhy

    enabled: true
    phyChip.text: vm.phyName
    unavailableBanner.visible: !vm.available
    unavailableLabel.text: vm.unavailableText
    visualizer.segments: vm.segments
    visualizer.caption: vm.caption

    modeControl.currentIndex: vm.mode === "TX" ? 1 : 0
    modeControl.onActivated: vm.setMode(index === 1 ? "TX" : "RX")
    standardCombo.model: vm.standards
    standardCombo.currentIndex: vm.standards.indexOf(vm.standard)
    standardCombo.onActivated: vm.setStandard(vm.standards[index])
    channelCombo.model: vm.channelOptions
    channelCombo.currentIndex: vm.channelOptions.indexOf(vm.channel)
    channelCombo.onActivated: vm.setChannel(vm.channelOptions[index])
    powerCombo.model: vm.powerModes
    powerCombo.currentIndex: vm.powerModes.indexOf(vm.powerMode)
    powerCombo.onActivated: vm.setPowerMode(vm.powerModes[index])
    rateCombo.model: vm.rateOptions
    rateCombo.currentIndex: vm.rateOptions.indexOf(vm.rate)
    rateCombo.onActivated: vm.setRate(vm.rateOptions[index])

    txSection.visible: vm.mode === "TX"
    lengthField.text: vm.pktLength
    lengthField.onEditingFinished: vm.setPktLength(lengthField.text)
    countField.text: vm.numPkts
    countField.onEditingFinished: vm.setNumPkts(countField.text)
    transmitCombo.model: vm.transmitModes
    transmitCombo.currentIndex: vm.transmitModes.indexOf(vm.transmitMode)
    transmitCombo.onActivated: vm.setTransmitMode(vm.transmitModes[index])
    aggrBox.checked: vm.aggrEnable
    aggrBox.onClicked: vm.setAggrEnable(aggrBox.checked)

    advancedSection.visible: vm.advancedAvailable
    advancedBox.checked: vm.advancedEnabled
    advancedBox.onClicked: vm.setAdvancedEnabled(advancedBox.checked)
    advancedGrid.enabled: vm.advancedEnabled
    advancedGrid.opacity: vm.advancedEnabled ? 1 : 0.5
    ppduCombo.model: vm.ppduTypes
    ppduCombo.currentIndex: vm.ppduTypes.indexOf(vm.ppduType)
    ppduCombo.onActivated: vm.setPpduType(vm.ppduTypes[index])
    giCombo.model: vm.giLtfOptions
    giCombo.currentIndex: vm.giLtfOptions.indexOf(vm.giLtf)
    giCombo.onActivated: vm.setGiLtf(vm.giLtfOptions[index])
    bandwidthCombo.model: vm.bandwidths
    bandwidthCombo.currentIndex: vm.bandwidths.indexOf(vm.bandwidth)
    bandwidthCombo.onActivated: vm.setBandwidth(vm.bandwidths[index])
    dcmBox.checked: vm.dcm
    dcmBox.onClicked: vm.setDcm(dcmBox.checked)

    problemLabel.text: vm.problems
    problemLabel.visible: vm.problems !== ""
    applyButton.text: vm.busy ? "Loading…" : "Apply configuration"
    applyButton.enabled: vm.canApply
    applyButton.onClicked: vm.apply()
    addButton.onClicked: vm.addToActions()
}
