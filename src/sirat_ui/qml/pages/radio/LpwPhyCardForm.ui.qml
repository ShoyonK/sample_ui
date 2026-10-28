import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 23 Load LPW PHY: a PHY name (pick, type, or take from a file), Load, Add to Actions.
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias currentChip: currentChip
    property alias phyField: phyField
    property alias knownCombo: knownCombo
    property alias browseButton: browseButton
    property alias loadButton: loadButton
    property alias addButton: addButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader {
            title: "Load LPW PHY"
            meta: "BLE and 802.15.4"
            Layout.fillWidth: true
            Chip { id: currentChip; objectName: "currentPhyChip"; text: "PHY: none"; tone: "mute"; mono: true }
        }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10
            Text {
                text: "Resets the DUT and downloads the PHY (reset_and_download_lpw_phy). Pick a name, type one, or take it from a PHY file."
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            RowLayout {
                spacing: 8
                Layout.fillWidth: true
                AppTextField {
                    id: phyField
                    objectName: "lpwPhyField"
                    mono: true
                    placeholderText: "BLE_1M"
                    Layout.fillWidth: true
                }
                AppComboBox {
                    id: knownCombo
                    objectName: "lpwKnownCombo"
                    displayText: "Known PHYs"
                    implicitHeight: 28
                    Layout.preferredWidth: 150
                }
                AppButton { id: browseButton; objectName: "lpwBrowseButton"; text: "PHY file…"; iconName: "upload"; small: true }
            }
            RowLayout {
                spacing: 8
                AppButton { id: loadButton; objectName: "lpwLoadButton"; text: "Load PHY"; iconName: "download"; variant: "primary" }
                AppButton { id: addButton; objectName: "lpwAddToActionsButton"; text: "Add to Actions"; iconName: "bolt" }
            }
        }
    }
}
