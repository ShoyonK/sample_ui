import QtQuick 2.15
import "../../theme"

Rectangle {
    id: row
    property bool selected: false
    signal activated()

    objectName: "function_" + modelData
    width: ListView.view ? ListView.view.width : 240
    height: Theme.rowHeight + 4
    color: selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
    HoverHandler { id: hover }
    TapHandler { onTapped: row.activated() }

    Rectangle { visible: row.selected; width: 2; height: parent.height; color: Theme.textPrimary }
    Text {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        text: modelData
        elide: Text.ElideRight
        font.family: Theme.fontMono
        font.pixelSize: Theme.fontSm
        font.weight: row.selected ? Font.DemiBold : Font.Normal
        color: Theme.textPrimary
    }
}
