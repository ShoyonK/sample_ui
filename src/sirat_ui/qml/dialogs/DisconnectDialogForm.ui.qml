import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Disconnect recovery (req 3): reconnect, then optionally reload a PHY.
ColumnLayout {
    id: root
    width: 500
    spacing: 14

    property alias header: header
    property alias details: details
    property alias statusLabel: statusLabel
    property alias closeButton: closeButton
    property alias lpwButton: lpwButton
    property alias wifiButton: wifiButton
    property alias reconnectButton: reconnectButton
    property alias addToActionsButton: addToActionsButton

    DialogHeader {
        id: header
        title: "DUT 1 connection lost"
        message: "Usually a power cycle, a J-Link disconnect, or a firmware assert."
        iconName: "plug"
        tone: "danger"
        Layout.fillWidth: true
        Layout.topMargin: 18
        Layout.leftMargin: 20
        Layout.rightMargin: 20
    }
    KeyValueGrid {
        id: details
        monoValues: false
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
    }
    Text {
        id: statusLabel
        objectName: "recoveryStatus"
        visible: text !== ""
        text: ""
        wrapMode: Text.WordWrap
        font.pixelSize: Theme.fontSm
        color: Theme.okFg
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
    }
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
        Layout.bottomMargin: 18
        spacing: Theme.s2
        AppButton { id: closeButton; objectName: "recoveryCloseButton"; text: "Close" }
        AppButton { id: addToActionsButton; objectName: "addReconnectToActionsButton"; text: "Add to Actions"; iconName: "bolt"; variant: "ghost" }
        Item { Layout.fillWidth: true }
        AppButton { id: lpwButton; objectName: "loadLpwPhyButton"; text: "Load LPW PHY" }
        AppButton { id: wifiButton; objectName: "loadWifiPhyButton"; text: "Load WiFi PHY" }
        AppButton { id: reconnectButton; objectName: "reconnectButton"; text: "Reconnect"; iconName: "refresh"; variant: "primary" }
    }
}
