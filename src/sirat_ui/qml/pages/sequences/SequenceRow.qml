import QtQuick 2.15
import "../../theme"

Rectangle {
    id: row
    signal activated()

    objectName: "sequence_" + model.name
    width: ListView.view ? ListView.view.width : 280
    height: 52
    color: model.selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
    HoverHandler { id: hover }
    TapHandler { onTapped: row.activated() }

    Column {
        anchors.left: parent.left
        anchors.leftMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            text: model.name
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontMd
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }
        Text {
            text: model.detail
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.border
    }
}
