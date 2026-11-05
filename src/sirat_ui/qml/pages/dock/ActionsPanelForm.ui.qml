import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 13 panel: View, Edit, Run, Run checked, Generate code; above the list, a checkbox for all actions (with
// Up, Down, Delete, Delete all as icons in the dock); the large view has those as buttons, plus Add to sequence
// and the console.
Card {
    id: root
    width: 600
    height: 230

    property alias header: header
    property alias viewButton: viewButton
    property alias editButton: editButton
    property alias runButton: runButton
    property alias runSelectedButton: runSelectedButton
    property alias codeButton: codeButton
    property alias list: list
    property alias footer: footer
    property alias upButton: upButton
    property alias downButton: downButton
    property alias deleteButton: deleteButton
    property alias deleteAllButton: deleteAllButton
    property alias allBox: allBox
    property alias checkedLabel: checkedLabel
    property alias dockTools: dockTools
    property alias dockUpButton: dockUpButton
    property alias dockDownButton: dockDownButton
    property alias dockDeleteButton: dockDeleteButton
    property alias dockDeleteAllButton: dockDeleteAllButton
    property alias addToSequenceButton: addToSequenceButton
    property alias runConsole: runConsole

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            id: header
            title: "Actions"
            meta: "synced with the Actions page"
            Layout.fillWidth: true
            AppButton { id: viewButton; objectName: "actionsViewButton"; text: "View"; iconName: "eye"; small: true }
            AppButton { id: editButton; objectName: "actionsEditButton"; text: "Edit"; iconName: "edit"; small: true }
            AppButton { id: runButton; objectName: "actionsRunButton"; text: "Run"; iconName: "play"; small: true; variant: "run" }
            AppButton { id: runSelectedButton; objectName: "actionsRunSelectedButton"; text: "Run checked"; iconName: "next"; small: true; variant: "run" }
            AppButton { id: codeButton; objectName: "actionsCodeButton"; text: "Code"; iconName: "code"; small: true }
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: 34
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.s3
                anchors.rightMargin: Theme.s3
                spacing: Theme.s2
                AppCheckBox { id: allBox; objectName: "actionsAllCheck"; accessibleName: "Check or uncheck every action"; tristate: true }
                Text {
                    id: checkedLabel
                    objectName: "actionsCheckedLabel"
                    text: "3 of 4 checked"
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                    Layout.fillWidth: true
                }
                Row {
                    id: dockTools
                    spacing: 2
                    IconButton { id: dockUpButton; objectName: "dockActionUpButton"; iconName: "up"; tip: "Move the selected action up" }
                    IconButton { id: dockDownButton; objectName: "dockActionDownButton"; iconName: "down"; tip: "Move the selected action down" }
                    IconButton { id: dockDeleteButton; objectName: "dockActionDeleteButton"; iconName: "delete"; tip: "Delete the selected action" }
                    IconButton { id: dockDeleteAllButton; objectName: "dockActionDeleteAllButton"; iconName: "erase"; tip: "Delete all actions" }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        }

        ListView {
            id: list
            objectName: "actionsList"
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: AppScrollBar {}
            delegate: ActionRow {}
        }

        Rectangle {
            visible: footer.visible
            Layout.fillWidth: true
            implicitHeight: 1
            color: Theme.border
        }

        Row {
            id: footer
            visible: false
            spacing: 6
            Layout.margins: Theme.s2
            AppButton { id: upButton; objectName: "actionUpButton"; text: "Up"; iconName: "up"; small: true }
            AppButton { id: downButton; objectName: "actionDownButton"; text: "Down"; iconName: "down"; small: true }
            AppButton { id: addToSequenceButton; objectName: "actionAddToSequenceButton"; text: "Add checked to sequence…"; iconName: "list"; small: true }
            AppButton { id: deleteButton; objectName: "actionDeleteButton"; text: "Delete"; iconName: "delete"; small: true }
            AppButton { id: deleteAllButton; objectName: "actionDeleteAllButton"; text: "Delete all"; small: true; variant: "danger" }
        }

        ConsolePanel {
            id: runConsole
            objectName: "actionsConsole"
            visible: footer.visible
            title: "Run output"
            Layout.fillWidth: true
            Layout.preferredHeight: 200
            Layout.margins: Theme.s2
            Layout.topMargin: 0
        }
    }
}
