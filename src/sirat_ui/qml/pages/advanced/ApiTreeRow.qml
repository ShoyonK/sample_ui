import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One row of the DUT control API tree: package › module › method (req 22 "Tree Icons").
Rectangle {
    id: row
    signal activated()

    objectName: "api_" + model.key
    width: ListView.view ? ListView.view.width : 340
    height: Theme.rowHeight
    color: model.selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
    HoverHandler { id: hover }
    TapHandler { onTapped: row.activated() }
    Accessible.role: model.kind === "method" ? Accessible.ListItem : Accessible.Button
    Accessible.name: model.label

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s2 + model.depth * 16
        anchors.rightMargin: Theme.s3
        spacing: 6
        Icon {
            name: model.kind === "method" ? "" : (model.expanded ? "chevronDown" : "chevronRight")
            size: 10
            Layout.preferredWidth: 12
        }
        Icon {
            name: model.kind === "package" ? "box" : model.kind === "module" ? "list" : "bolt"
            size: 12
            color: model.kind === "method" ? Theme.infoFg : Theme.textMuted
        }
        Text {
            text: model.label
            elide: Text.ElideRight
            font.family: model.kind === "package" ? Theme.fontUi : Theme.fontMono
            font.pixelSize: Theme.fontSm
            font.weight: model.kind === "package" || model.selected ? Font.DemiBold : Font.Normal
            color: Theme.textPrimary
            Layout.fillWidth: true
        }
        Text {
            visible: model.kind !== "method"
            text: model.count
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }
}
