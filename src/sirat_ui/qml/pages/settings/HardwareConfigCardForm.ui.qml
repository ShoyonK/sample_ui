import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 32 Hardware Configuration: RPC host/port/timeout, DUT position, Save, Test Connection, status.
Card {
    id: root
    width: 700
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias overrideBox: overrideBox
    property alias hostField: hostField
    property alias portField: portField
    property alias timeoutField: timeoutField
    property alias positionField: positionField
    property alias hostError: hostError
    property alias portError: portError
    property alias timeoutError: timeoutError
    property alias positionError: positionError
    property alias saveButton: saveButton
    property alias testButton: testButton
    property alias statusLabel: statusLabel

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "Hardware configuration"; meta: "saved to ~/.sirat/hardware_config.json"; Layout.fillWidth: true }

        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10

            Text { text: "RPC connection"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary }
            AppCheckBox {
                id: overrideBox
                objectName: "hwOverrideBox"
                text: "Use a specific RPC address (otherwise the station's workspace config decides)"
            }
            GridLayout {
                columns: 3
                columnSpacing: 12
                rowSpacing: 6
                Layout.fillWidth: true

                Text { text: "Host"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 90 }
                AppTextField { id: hostField; objectName: "hwHostField"; placeholderText: "localhost"; Layout.preferredWidth: 250 }
                Text { id: hostError; text: ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; Layout.fillWidth: true }

                Text { text: "Port"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: portField; objectName: "hwPortField"; mono: true; selectOnFocus: true; placeholderText: "10001"; Layout.preferredWidth: 150 }
                Text { id: portError; text: ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; Layout.fillWidth: true }

                Text { text: "Timeout (s)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: timeoutField; objectName: "hwTimeoutField"; mono: true; selectOnFocus: true; placeholderText: "5"; Layout.preferredWidth: 150 }
                Text { id: timeoutError; text: ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; Layout.fillWidth: true }
            }

            Text { text: "DUT"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; Layout.topMargin: 4 }
            GridLayout {
                columns: 3
                columnSpacing: 12
                Layout.fillWidth: true
                Text { text: "Position"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 90 }
                AppTextField { id: positionField; objectName: "hwPositionField"; mono: true; selectOnFocus: true; placeholderText: "1"; Layout.preferredWidth: 150 }
                Text { id: positionError; text: ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; Layout.fillWidth: true }
            }

            Text {
                text: "Host and port are sent with Connect and Test connection only while the box above is checked; the Connect sheet can change them for one connection. The timeout is applied to the station when you save."
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
            }

            RowLayout {
                spacing: 8
                Layout.topMargin: 4
                AppButton { id: saveButton; objectName: "hwSaveButton"; text: "Save"; iconName: "save"; variant: "primary" }
                AppButton { id: testButton; objectName: "hwTestButton"; text: "Test connection"; iconName: "plug" }
                Text {
                    id: statusLabel
                    objectName: "hwStatus"
                    text: "Modify settings and click Save"
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    Layout.leftMargin: 6
                }
            }
        }
    }
}
