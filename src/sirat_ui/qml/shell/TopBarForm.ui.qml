import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Rectangle {
    id: root
    implicitHeight: 48
    color: Theme.surface

    property alias chipChip: chipChip
    property alias positionControl: positionControl
    property alias connectionPill: connectionPill
    property alias recoverButton: recoverButton
    property alias phyChip: phyChip
    property alias searchButton: searchButton
    property alias connectionButton: connectionButton
    property alias themeButton: themeButton

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: Theme.s3

        Text {
            text: "SiRAT"
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontHeading
            font.weight: Font.Bold
            color: Theme.textPrimary
        }
        Chip {
            id: chipChip
            objectName: "chipLabel"
            text: "EFR32XG29XFULL · revA0"
            mono: true
        }
        Text {
            text: "DUT"
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
        }
        SegmentedControl {
            id: positionControl
            objectName: "positionControl"
            model: ["1", "2", "3", "4"]
        }
        StatusPill {
            id: connectionPill
            objectName: "connectionPill"
            text: "Connected"
        }
        AppButton {
            id: recoverButton
            objectName: "recoverButton"
            text: "Recover"
            iconName: "refresh"
            variant: "danger"
            small: true
        }
        Chip {
            id: phyChip
            text: "PHY · BLE_1M"
            tone: "info"
            visible: text !== ""
        }
        Item {
            Layout.fillWidth: true
        }
        AppButton {
            id: searchButton
            objectName: "searchButton"
            text: "Jump to register, page or action    Ctrl K"
            iconName: "search"
            Layout.preferredWidth: 320
        }
        AppButton {
            id: connectionButton
            objectName: "connectionButton"
            text: "Connection"
            iconName: "plug"
        }
        IconButton {
            id: themeButton
            objectName: "themeButton"
            iconName: "moon"
            tip: "Toggle dark mode"
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.border
    }
}
