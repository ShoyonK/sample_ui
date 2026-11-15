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
            Text { text: "Show"; height: 24; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            SegmentedControl {
                id: filterControl
                objectName: "historyFilter"
                model: ["Read", "Write"]
                multi: true
                small: true
                checkedStates: [true, true]
            }
            Rectangle { width: 1; height: 18; y: 3; color: Theme.border }
            AppButton { id: runButton; objectName: "historyRunButton"; text: "Run"; iconName: "play"; small: true; variant: "run" }
            AppButton { id: createActionButton; objectName: "createActionButton"; text: "Create action"; iconName: "bolt"; small: true }
            AppButton { id: codeButton; objectName: "historyCodeButton"; text: "Code"; iconName: "code"; small: true }
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
