import QtQuick 2.15

RfSwitchCardForm {
    readonly property var vm: app.rfSwitch

    status.text: vm.instrumentText
    status.found: vm.instrumentFound
    status.connected: vm.instrumentConnected
    status.onConnectRequested: vm.connectInstrument()
    pathCombo.model: vm.paths
    pathCombo.currentIndex: vm.pathIndex
    pathCombo.onActivated: vm.setPath(index)
    positionCombo.model: vm.positions
    positionCombo.currentIndex: vm.positionIndex
    positionCombo.onActivated: vm.setPosition(index)
    currentLabel.text: vm.currentText
    connectButton.enabled: vm.canConnect
    connectButton.busy: vm.busy
    connectButton.onClicked: vm.connectPath()
    disconnectButton.enabled: vm.canDisconnect
    disconnectButton.onClicked: vm.disconnectPath()
    addButton.enabled: vm.pathIndex >= 0
    addButton.onClicked: vm.addToActions()
}
