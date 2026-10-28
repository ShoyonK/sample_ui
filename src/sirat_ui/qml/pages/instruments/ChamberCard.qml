import QtQuick 2.15

ChamberCardForm {
    id: card
    readonly property var vm: app.chamber

    status.text: vm.instrumentText
    status.found: vm.instrumentFound
    status.connected: vm.instrumentConnected
    status.onConnectRequested: vm.connectInstrument()
    actualLabel.text: vm.actualText
    trendPill.text: vm.trendText
    trendPill.visible: vm.trendText !== ""
    trendPill.level: vm.stable ? "ok" : vm.trendText === "Heating" ? "warn" : "info"
    setpointLabel.text: vm.setpointText
    trendLine.points: vm.history
    targetField.text: vm.target
    targetField.onTextEdited: vm.setField("target", targetField.text)
    targetField.invalid: !!vm.errors.target
    setButton.enabled: vm.canSet
    setButton.onClicked: vm.setTemperature()
    intervalField.text: vm.interval
    intervalField.onTextEdited: vm.setField("interval", intervalField.text)
    intervalField.invalid: !!vm.errors.interval
    toleranceField.text: vm.tolerance
    toleranceField.onTextEdited: vm.setField("tolerance", toleranceField.text)
    toleranceField.invalid: !!vm.errors.tolerance
    holdField.text: vm.hold
    holdField.onTextEdited: vm.setField("hold", holdField.text)
    holdField.invalid: !!vm.errors.hold
    waitButton.enabled: vm.canWait
    waitButton.visible: !vm.waiting
    stopButton.visible: vm.waiting
    stopButton.onClicked: vm.abortWait()
    waitButton.onClicked: vm.waitForStable()
    waitLabel.text: vm.waitText
    errorLabel.text: vm.errorText

    // Poll the chamber only while the card is on screen (the page stays loaded when you leave it).
    onVisibleChanged: vm.setActive(visible)
    Component.onCompleted: vm.setActive(visible)
    Component.onDestruction: vm.setActive(false)
}
