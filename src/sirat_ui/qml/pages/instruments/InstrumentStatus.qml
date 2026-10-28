import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// An instrument card's first line: which instrument, whether it's connected, and Connect after a drop.
RowLayout {
    id: root
    property string text: ""
    property bool found: true
    property bool connected: true
    property string prefix: ""        // objectName prefix, e.g. "sg" -> sgConnectButton
    signal connectRequested()

    spacing: 8
    StatusPill {
        objectName: root.prefix + "InstrumentPill"
        text: root.connected ? "Connected" : root.found ? "Disconnected" : "Not on this station"
        level: root.connected ? "ok" : root.found ? "danger" : "warn"
        compact: true
    }
    Text {
        objectName: root.prefix + "InstrumentText"
        text: root.text
        font.family: Theme.fontMono
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
        elide: Text.ElideRight
        Layout.fillWidth: true
    }
    AppButton {
        objectName: root.prefix + "ConnectButton"
        text: "Connect"
        iconName: "plug"
        small: true
        visible: root.found && !root.connected
        onClicked: root.connectRequested()
    }
}
