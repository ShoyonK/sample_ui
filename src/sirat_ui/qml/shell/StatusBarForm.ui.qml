import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    id: root
    implicitHeight: 26
    color: Theme.surface

    property alias messageLabel: messageLabel
    property alias backendLabel: backendLabel
    property alias releaseLabel: releaseLabel
    property alias activityLabel: activityLabel

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: Theme.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 14

        Text {
            id: messageLabel
            objectName: "statusMessage"
            text: "BUFC.LPMODE @ 0xBA000008 · read ok"
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            id: backendLabel
            text: "Fake backend · scenario happy"
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
        Text {
            id: releaseLabel
            text: "Service fake-2026.10"
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
        Text {
            id: activityLabel
            text: "Activity idle"
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }
}
