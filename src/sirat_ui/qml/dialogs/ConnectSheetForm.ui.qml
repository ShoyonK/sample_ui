import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Connect to DUT (req 3): position, config type, optional config file, live console.
Rectangle {
    id: root
    width: 420
    height: 900
    color: Theme.surface

    property alias closeIcon: closeIcon
    property alias positionControl: positionControl
    property alias configTypeControl: configTypeControl
    property alias configFileField: configFileField
    property alias overrideBox: overrideBox
    property alias hostField: hostField
    property alias portField: portField
    property alias consoleList: consoleList
    property alias disconnectButton: disconnectButton
    property alias closeButton: closeButton
    property alias connectButton: connectButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            title: "Connect to DUT"
            Layout.fillWidth: true
            IconButton { id: closeIcon; objectName: "connectSheetCloseIcon"; iconName: "close"; tip: "Close" }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.s4
            spacing: Theme.s3

            Text { text: "DUT position"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
            SegmentedControl { id: positionControl; objectName: "connectPositionControl"; model: ["1", "2", "3", "4"] }
            Text { text: "Config type"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
            SegmentedControl { id: configTypeControl; objectName: "configTypeControl"; model: ["EFX", "EFR32"]; currentIndex: 1 }
            Text { text: "Config file"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
            AppTextField {
                id: configFileField
                objectName: "configFileField"
                placeholderText: "Leave empty for the station default"
                Layout.fillWidth: true
            }
            Text { text: "RPC address"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
            AppCheckBox { id: overrideBox; objectName: "connectOverrideBox"; text: "Use a specific address for this connection" }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.s2
                AppTextField { id: hostField; objectName: "connectHostField"; placeholderText: "localhost"; Layout.fillWidth: true }
                AppTextField { id: portField; objectName: "connectPortField"; mono: true; placeholderText: "10001"; Layout.preferredWidth: 90 }
            }
            Text {
                text: "Unchecked, the station uses its workspace config. Defaults come from Settings."
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            Text { text: "Output"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.consoleBg
                ListView {
                    id: consoleList
                    objectName: "connectConsole"
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    delegate: Text {
                        width: ListView.view ? ListView.view.width : 380
                        text: (model.level === "success" ? "✓ " : model.level === "error" ? "✗ " : "") + model.text
                        wrapMode: Text.WrapAnywhere
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontXs
                        lineHeight: 1.4
                        color: model.level === "success" ? "#7EE29A" : model.level === "error" ? "#FF8A8A"
                             : model.level === "warning" ? "#FFC66B" : Theme.consoleText
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.s3
            spacing: Theme.s2
            AppButton { id: disconnectButton; objectName: "disconnectButton"; text: "Disconnect"; variant: "danger" }
            Item { Layout.fillWidth: true }
            AppButton { id: closeButton; objectName: "connectSheetCloseButton"; text: "Close" }
            AppButton { id: connectButton; objectName: "connectButton"; text: "Connect"; iconName: "plug"; variant: "primary" }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Theme.border
    }
}
