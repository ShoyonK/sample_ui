import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../pages/dock"

// History | Actions | Log, always visible under every page (req 2).
Item {
    id: root
    width: 1500
    height: 230

    RowLayout {
        anchors.fill: parent
        spacing: 10

        HistoryPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 6
        }
        ActionsPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 6
        }
        LogPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 5
        }
    }
}
