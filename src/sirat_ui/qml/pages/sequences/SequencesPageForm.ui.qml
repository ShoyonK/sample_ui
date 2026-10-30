import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 14 Sequence Manager: sequences on the left; the selected sequence's actions, editing buttons,
// run/abort and a console on the right.
RowLayout {
    id: root
    width: 1500
    height: 760
    spacing: 10

    property alias newButton: newButton
    property alias renameButton: renameButton
    property alias deleteButton: deleteButton
    property alias toActionsButton: toActionsButton
    property alias sequenceList: sequenceList
    property alias titleLabel: titleLabel
    property alias statusChip: statusChip
    property alias codeButton: codeButton
    property alias runButton: runButton
    property alias progressBar: progressBar
    property alias messageLabel: messageLabel
    property alias addActionButton: addActionButton
    property alias removeStepButton: removeStepButton
    property alias stepUpButton: stepUpButton
    property alias stepDownButton: stepDownButton
    property alias stepList: stepList
    property alias runConsole: runConsole

    Card {
        Layout.preferredWidth: 300
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                title: "Sequences"
                Layout.fillWidth: true
                AppButton { id: newButton; objectName: "newSequenceButton"; text: "New"; iconName: "add"; small: true }
            }
            ListView {
                id: sequenceList
                objectName: "sequenceList"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                delegate: SequenceRow {}
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }
            Flow {
                Layout.fillWidth: true
                Layout.margins: Theme.s2
                spacing: 6
                AppButton { id: renameButton; objectName: "renameSequenceButton"; text: "Rename"; iconName: "edit"; small: true }
                AppButton { id: toActionsButton; objectName: "sequenceToActionsButton"; text: "Add to Actions"; iconName: "bolt"; small: true }
                AppButton { id: deleteButton; objectName: "deleteSequenceButton"; text: "Delete"; iconName: "delete"; small: true; variant: "ghost" }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Item {
                Layout.fillWidth: true
                implicitHeight: Theme.headerHeight
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s3
                    anchors.rightMargin: Theme.s3
                    spacing: Theme.s2
                    Text {
                        id: titleLabel
                        text: "ble_rx_bringup"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.Bold
                        color: Theme.textPrimary
                    }
                    Chip { id: statusChip; text: "Running · action 2 of 2"; tone: "info" }
                    Item { Layout.fillWidth: true }
                    AppButton { id: codeButton; objectName: "sequenceCodeButton"; text: "Generate code"; iconName: "code"; small: true }
                    AppButton { id: runButton; objectName: "runSequenceButton"; text: "Run"; iconName: "play"; small: true; variant: "run" }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            }

            Column {
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 6
                Rectangle {
                    width: parent.width
                    height: 6
                    radius: 3
                    color: Theme.select
                    Rectangle {
                        id: progressBar
                        objectName: "sequenceProgress"
                        width: parent.width * 0.5
                        height: parent.height
                        radius: 3
                        color: Theme.textPrimary
                    }
                }
                Text {
                    id: messageLabel
                    text: "ble_1m_rx_setup: Load PHY BLE_1M…"
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.s3
                Layout.rightMargin: Theme.s3
                Layout.bottomMargin: Theme.s2
                spacing: 6
                Text {
                    text: "Actions in this sequence"
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                    Layout.fillWidth: true
                }
                AppButton { id: addActionButton; objectName: "addStepButton"; text: "Add action…"; iconName: "add"; small: true }
                AppButton { id: removeStepButton; objectName: "removeStepButton"; text: "Remove"; iconName: "delete"; small: true }
                AppButton { id: stepUpButton; objectName: "stepUpButton"; text: "Up"; iconName: "up"; small: true }
                AppButton { id: stepDownButton; objectName: "stepDownButton"; text: "Down"; iconName: "down"; small: true }
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

            ListView {
                id: stepList
                objectName: "stepList"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: StepRow {}
            }

            ConsolePanel {
                id: runConsole
                objectName: "sequenceConsole"
                title: "Console"
                Layout.fillWidth: true
                Layout.preferredHeight: 170
                Layout.margins: Theme.s2
            }
        }
    }
}
