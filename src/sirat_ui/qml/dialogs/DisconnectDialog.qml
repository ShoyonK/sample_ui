import QtQuick 2.15
import "../theme"
import "../components"

ModalDialog {
    id: dialog
    objectName: "disconnectDialog"
    readonly property var vm: app.recovery

    visible: vm.visible
    dialogWidth: 520

    contentItem: DisconnectDialogForm {
        header.title: "DUT " + dialog.vm.position + " connection lost"
        details.rows: [
            { key: "Cause", value: dialog.vm.cause },
            { key: "Detected by", value: dialog.vm.detectedBy },
            { key: "Cleared", value: "PHY loaded, watch, radio config" }
        ]
        statusLabel.text: dialog.vm.statusText
        statusLabel.color: Theme.toneFg(dialog.vm.statusLevel === "danger" ? "danger"
                                        : dialog.vm.statusLevel === "ok" ? "ok" : "mute")
        closeButton.onClicked: dialog.vm.dismiss()
        addToActionsButton.onClicked: dialog.vm.addReconnectToActions()
        lpwButton.enabled: dialog.vm.reconnected
        lpwButton.onClicked: dialog.vm.loadLpwPhy()
        wifiButton.enabled: dialog.vm.reconnected && dialog.vm.wifiAvailable
        wifiButton.onClicked: dialog.vm.loadWifiPhy()
        reconnectButton.text: dialog.vm.reconnected ? "Connected" : dialog.vm.busy ? "Reconnecting…" : "Reconnect"
        reconnectButton.iconName: dialog.vm.reconnected ? "check" : "refresh"
        reconnectButton.busy: dialog.vm.busy
        reconnectButton.enabled: !dialog.vm.busy && !dialog.vm.reconnected
        reconnectButton.onClicked: dialog.vm.reconnect()
    }
}
