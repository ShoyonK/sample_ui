import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Watch and logger: the watch list (req 18) and the data logger (req 17). Either can open in its own window;
// a placeholder takes its place here meanwhile.
RowLayout {
    id: root
    width: 1500
    height: 760
    spacing: 10

    property alias watchPanel: watchPanel
    property alias watchPlaceholder: watchPlaceholder
    property alias logger: logger
    property alias loggerPlaceholder: loggerPlaceholder

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true
        WatchListPanel { id: watchPanel; anchors.fill: parent }
        PoppedOutPlaceholder {
            id: watchPlaceholder
            objectName: "watchListPlaceholder"
            title: "The watch list"
            anchors.centerIn: parent
            width: Math.min(parent.width - 40, 480)
            visible: false
        }
    }

    Item {
        Layout.preferredWidth: 460
        Layout.fillHeight: true
        LoggerPanel { id: logger; anchors.fill: parent }
        PoppedOutPlaceholder {
            id: loggerPlaceholder
            objectName: "loggerPlaceholder"
            title: "The data logger"
            anchors.centerIn: parent
            width: parent.width - 20
            visible: false
        }
    }
}
