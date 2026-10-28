import QtQuick 2.15
import "../theme"
import "../components"

Rectangle {
    id: root
    implicitWidth: 56
    color: Theme.surface

    property alias pagesRepeater: pagesRepeater
    property alias settingsButton: settingsButton

    Column {
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 2

        Repeater {
            id: pagesRepeater
            model: ["registers", "watch", "actions", "sequences"]
            delegate: NavButton {
                pageKey: modelData
            }
        }
    }

    NavButton {
        id: settingsButton
        objectName: "nav_settings"
        pageKey: "settings"
        iconName: "settings"
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: Theme.border
    }
}
