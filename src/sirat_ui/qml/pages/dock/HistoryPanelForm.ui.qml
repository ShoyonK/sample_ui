import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

Card {
    id: root
    width: 600
    height: 230

    property alias filterControl: filterControl
    property alias runButton: runButton
    property alias createActionButton: createActionButton
    property alias codeButton: codeButton
    property alias copyButton: copyButton
    property alias clearButton: clearButton
    property alias list: list

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            title: "History"
            Layout.fillWidth: true
            SegmentedControl {
                id: filterControl
                objectName: "historyFilter"
                model: ["Read", "Write"]
                multi: true
                small: true
                checkedStates: [true, true]
            }
            AppButton { id: runButton; objectName: "historyRunButton"; text: "Run"; iconName: "play"; small: true }
            AppButton { id: createActionButton; objectName: "createActionButton"; text: "Create action"; iconName: "bolt"; small: true }
            IconButton { id: codeButton; objectName: "historyCodeButton"; iconName: "code"; tip: "Generate code (selected, or all)" }
            IconButton { id: copyButton; objectName: "historyCopyButton"; iconName: "copy"; tip: "Copy history" }
            IconButton { id: clearButton; objectName: "historyClearButton"; iconName: "delete"; tip: "Clear history" }
        }

        ListView {
            id: list
            objectName: "historyList"
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: AppScrollBar {}
            delegate: HistoryRow {}
        }
    }
}
