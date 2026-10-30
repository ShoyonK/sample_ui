import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 15 Custom Functions: the saved functions on the left (New, Rename, Delete); the highlighted editor,
// Run and Add to Actions, and the run output on the right.
RowLayout {
    id: root
    width: 1200
    height: 700
    spacing: 10

    property alias functionList: functionList
    property alias listEmpty: listEmpty
    property alias newButton: newButton
    property alias renameButton: renameButton
    property alias deleteButton: deleteButton
    property alias editorHeader: editorHeader
    property alias addButton: addButton
    property alias runButton: runButton
    property alias editor: editor
    property alias runHint: runHint
    property alias output: output
    property alias noSelection: noSelection

    Card {
        Layout.preferredWidth: 260
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                title: "Functions"
                Layout.fillWidth: true
                AppButton { id: newButton; objectName: "functionNewButton"; text: "New"; iconName: "add"; small: true }
            }
            ListView {
                id: functionList
                objectName: "functionList"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: FunctionRow {}
                EmptyState {
                    id: listEmpty
                    anchors.centerIn: parent
                    width: parent.width - 32
                    iconName: "code"
                    title: "No functions yet"
                    body: "New creates one. Functions are saved in ~/.sirat_custom_functions.json."
                }
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }
            RowLayout {
                spacing: 6
                Layout.margins: Theme.s2
                AppButton { id: renameButton; objectName: "functionRenameButton"; text: "Rename"; iconName: "edit"; small: true }
                AppButton { id: deleteButton; objectName: "functionDeleteButton"; text: "Delete"; iconName: "delete"; small: true; variant: "danger" }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                id: editorHeader
                monoTitle: true
                Layout.fillWidth: true
                AppButton { id: addButton; objectName: "functionAddToActionsButton"; text: "Add to Actions"; iconName: "bolt"; small: true }
                AppButton { id: runButton; objectName: "functionRunButton"; text: "Run"; iconName: "play"; small: true; variant: "run" }
            }
            ColumnLayout {
                spacing: Theme.s2
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: Theme.s3
                CodeEditor {
                    id: editor
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 3
                }
                Text {
                    id: runHint
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                OutputView {
                    id: output
                    prefix: "functions"
                    title: "Run output"
                    emptyText: "Print output, the result and any traceback appear here."
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 2
                }
            }
        }
        EmptyState {
            id: noSelection
            anchors.centerIn: parent
            iconName: "code"
            title: "Nothing selected"
            body: "Pick one on the left, or create one with New."
        }
    }
}
