import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"

Rectangle {
    id: row
    signal activated()

    objectName: "dump_" + model.name
    width: ListView.view ? ListView.view.width : 360
    height: 54
    color: model.selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
    HoverHandler { id: hover }
    TapHandler { onTapped: row.activated() }

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        RowLayout {
            width: parent.width
            Text {
                text: model.name
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                color: Theme.textPrimary
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text { text: model.time; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
        }
        Text {
            text: model.detail
            width: parent.width
            elide: Text.ElideRight
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }

    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
}
