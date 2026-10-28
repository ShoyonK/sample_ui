import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// The collapsed dock: one line with the newest history entry, the checked actions, and the newest log line.
// Clicking anywhere on it opens the dock.
Rectangle {
    id: root
    width: 1500
    implicitHeight: 34
    radius: Theme.radius
    color: Theme.surface
    border.color: Theme.border

    property alias toggleButton: toggleButton
    property alias historyArea: historyArea
    property alias historyText: historyText
    property alias actionsArea: actionsArea
    property alias actionsText: actionsText
    property alias runButton: runButton
    property alias logArea: logArea
    property alias logDot: logDot
    property alias logText: logText

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s1
        anchors.rightMargin: Theme.s2
        spacing: 0

        IconButton {
            id: toggleButton
            objectName: "dockToggle"
            iconName: "up"
            tip: "Show History, Actions and Log"
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            MouseArea { id: historyArea; objectName: "dockHistorySegment"; Accessible.role: Accessible.Button; Accessible.name: "Open History"; anchors.fill: parent; cursorShape: Qt.PointingHandCursor }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.s2
                anchors.rightMargin: Theme.s3
                spacing: Theme.s2
                Text { text: "History"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                Text {
                    id: historyText
                    text: "Write  BUFC.LPMODE = 0x3"
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontXs
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        Rectangle { width: 1; Layout.fillHeight: true; Layout.topMargin: 8; Layout.bottomMargin: 8; color: Theme.border }

        Item {
            Layout.fillWidth: true
            Layout.preferredWidth: 5
            Layout.fillHeight: true
            MouseArea { id: actionsArea; objectName: "dockActionsSegment"; Accessible.role: Accessible.Button; Accessible.name: "Open Actions"; anchors.fill: parent; cursorShape: Qt.PointingHandCursor }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.s3
                anchors.rightMargin: Theme.s3
                spacing: Theme.s2
                Text { text: "Actions"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                Text {
                    id: actionsText
                    text: "3 checked"
                    font.pixelSize: Theme.fontXs
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }
                AppButton { id: runButton; objectName: "dockRunChecked"; text: "Run checked"; iconName: "play"; small: true }
            }
        }

        Rectangle { width: 1; Layout.fillHeight: true; Layout.topMargin: 8; Layout.bottomMargin: 8; color: Theme.border }

        Item {
            Layout.fillWidth: true
            Layout.preferredWidth: 7
            Layout.fillHeight: true
            MouseArea { id: logArea; objectName: "dockLogSegment"; Accessible.role: Accessible.Button; Accessible.name: "Open Log"; anchors.fill: parent; cursorShape: Qt.PointingHandCursor }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.s3
                spacing: Theme.s2
                Text { text: "Log"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textPrimary }
                Rectangle { id: logDot; width: 6; height: 6; radius: 3; color: Theme.okFg }
                Text {
                    id: logText
                    text: "Wrote BUFC.LPMODE = 0x3 · verified"
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontXs
                    color: Theme.textPrimary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
    }
}
