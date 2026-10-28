import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 13 panel: list + View, Edit, Run, Run checked, Generate code; second row (large view):
// Delete, Delete all, Deselect all, Up, Down, Add to sequence; console under the large view.
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
    property alias deselectAllButton: deselectAllButton
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
            IconButton { id: viewButton; objectName: "actionsViewButton"; iconName: "eye"; tip: "View the selected action" }
            IconButton { id: editButton; objectName: "actionsEditButton"; iconName: "edit"; tip: "Edit the selected action" }
            AppButton { id: runButton; objectName: "actionsRunButton"; text: "Run"; iconName: "play"; small: true }
            AppButton { id: runSelectedButton; objectName: "actionsRunSelectedButton"; text: "Run checked"; iconName: "next"; small: true; variant: "primary" }
            IconButton { id: codeButton; objectName: "actionsCodeButton"; iconName: "code"; tip: "Generate code" }
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
            AppButton { id: deselectAllButton; objectName: "actionDeselectAllButton"; text: "Deselect all"; small: true }
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
