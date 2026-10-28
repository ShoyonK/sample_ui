import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 28 RF Switch Control: switch status, path and DUT position, Connect path, Disconnect, Add to Actions.
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias status: status
    property alias pathCombo: pathCombo
    property alias positionCombo: positionCombo
    property alias currentLabel: currentLabel
    property alias connectButton: connectButton
    property alias disconnectButton: disconnectButton
    property alias addButton: addButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "RF switch"; meta: "route the bench's RF to a DUT"; Layout.fillWidth: true }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10

            InstrumentStatus { id: status; prefix: "rf"; Layout.fillWidth: true }

            GridLayout {
                columns: 2
                columnSpacing: 10
                rowSpacing: 4
                Layout.fillWidth: true
                Text { text: "Path"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                Text { text: "DUT position"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                AppComboBox { id: pathCombo; objectName: "rfPathCombo"; implicitHeight: 28; Layout.fillWidth: true; Layout.minimumWidth: 180 }
                AppComboBox { id: positionCombo; objectName: "rfPositionCombo"; implicitHeight: 28; Layout.preferredWidth: 90 }
            }
            RowLayout {
                spacing: 6
                Icon { name: "antenna"; size: 14; color: Theme.textMuted }
                Text {
                    id: currentLabel
                    objectName: "rfCurrent"
                    text: "DUT 1 has no RF path connected"
                    font.pixelSize: Theme.fontSm
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
            }
            RowLayout {
                spacing: 8
                AppButton { id: connectButton; objectName: "rfConnectButton"; text: "Connect path"; iconName: "plug"; variant: "primary" }
                AppButton { id: disconnectButton; objectName: "rfDisconnectButton"; text: "Disconnect"; iconName: "close" }
                AppButton { id: addButton; objectName: "rfAddToActionsButton"; text: "Add to Actions"; iconName: "bolt" }
            }
        }
    }
}
