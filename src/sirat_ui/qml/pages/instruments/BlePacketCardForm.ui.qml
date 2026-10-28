import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 26 BLE Packet Configuration: access address, CRC init, whitening seed, preamble, sync word (derived),
// Generate code (the code window has Copy to clipboard and Save to file).
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias accessField: accessField
    property alias crcField: crcField
    property alias whiteningField: whiteningField
    property alias preambleField: preambleField
    property alias syncLabel: syncLabel
    property alias errorLabel: errorLabel
    property alias generateButton: generateButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "BLE packet"; meta: "saved to ~/.sirat/ble_packet.json"; Layout.fillWidth: true }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 6
                Layout.fillWidth: true

                Text { text: "Access address"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: accessField; objectName: "bleAccessField"; mono: true; placeholderText: "0x8E89BED6"; Layout.preferredWidth: 130 }
                Text { text: "CRC init"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: crcField; objectName: "bleCrcField"; mono: true; placeholderText: "0x555555"; Layout.preferredWidth: 110 }

                Text { text: "Whitening seed"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: whiteningField; objectName: "bleWhiteningField"; mono: true; selectOnFocus: true; placeholderText: "37"; Layout.preferredWidth: 130 }
                Text { text: "Preamble"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: preambleField; objectName: "blePreambleField"; mono: true; placeholderText: "0xAA"; Layout.preferredWidth: 110 }

                Text { text: "Sync word"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                Text {
                    id: syncLabel
                    objectName: "bleSyncWord"
                    text: "0x6B7D9171"
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSm
                    color: Theme.textPrimary
                    Layout.columnSpan: 3
                }
            }
            Text {
                text: "The sync word is the access address in on-air bit order (BLE sends it LSB first). Whitening seed is 0 to 127, usually the channel index."
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            Text { id: errorLabel; objectName: "bleErrors"; text: ""; visible: text !== ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                spacing: 8
                AppButton { id: generateButton; objectName: "bleGenerateButton"; text: "Generate code"; iconName: "code"; variant: "primary" }
            }
        }
    }
}
