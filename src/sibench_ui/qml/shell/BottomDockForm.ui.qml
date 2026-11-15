import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../pages/dock"

// History | Actions | Log under every page (req 2). Hidden, it collapses to the one-line strip.
Item {
    id: root
    width: 1500
    height: 230

    property bool collapsed: false
    property bool showActions: true   // the Actions page already shows the list
    readonly property real stripHeight: strip.implicitHeight
    property alias strip: strip

    DockStrip {
        id: strip
        visible: root.collapsed
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }

    RowLayout {
        visible: !root.collapsed
        anchors.fill: parent
        spacing: 10

        HistoryPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 6
        }
        ActionsPanel {
            visible: root.showActions
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 6
        }
        LogPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: root.showActions ? 5 : 7
        }
    }
}
