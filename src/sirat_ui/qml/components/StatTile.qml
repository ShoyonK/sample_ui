import QtQuick 2.15
import "../theme"

Rectangle {
    id: root
    property string label: ""
    property string value: ""

    implicitHeight: 64
    radius: Theme.radius
    color: Theme.surface2
    border.color: Theme.border

    Column {
        anchors.left: parent.left
        anchors.leftMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            text: root.label
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
        Text {
            text: root.value
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontXl
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }
    }
}
