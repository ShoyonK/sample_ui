import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

Drawer {
    id: sheet
    objectName: "connectSheet"
    readonly property var vm: app.connection

    edge: Qt.RightEdge
    width: 420
    height: parent ? parent.height - 74 : 800
    y: 48
    modal: false
    interactive: false
    visible: vm.sheetOpen
    background: Item {}

    contentItem: ConnectSheetForm {
        closeIcon.onClicked: sheet.vm.closeSheet()
        positionControl.currentIndex: sheet.vm.position - 1
        positionControl.onActivated: sheet.vm.setPosition(index + 1)
        configTypeControl.currentIndex: sheet.vm.configTypeIndex
        configTypeControl.onActivated: sheet.vm.setConfigTypeIndex(index)
        configFileField.text: sheet.vm.configFile
        configFileField.onEditingFinished: sheet.vm.setConfigFile(configFileField.text)
        overrideBox.checked: sheet.vm.override
        overrideBox.onClicked: sheet.vm.setOverride(overrideBox.checked)
        hostField.enabled: sheet.vm.override
        hostField.text: sheet.vm.rpcHost
        hostField.onTextEdited: sheet.vm.setRpcHost(hostField.text)
        portField.enabled: sheet.vm.override
        portField.text: sheet.vm.rpcPort
        portField.onTextEdited: sheet.vm.setRpcPort(portField.text)
        consoleList.model: sheet.vm.console
        disconnectButton.enabled: sheet.vm.connected && !sheet.vm.busy
        disconnectButton.onClicked: sheet.vm.disconnectDut()
        closeButton.onClicked: sheet.vm.closeSheet()
        connectButton.text: sheet.vm.busy ? "Connecting…" : "Connect"
        connectButton.busy: sheet.vm.busy
        connectButton.enabled: !sheet.vm.busy
        connectButton.onClicked: sheet.vm.connect()
    }
}
