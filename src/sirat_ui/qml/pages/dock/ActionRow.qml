import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One action: checkbox (enabled), type color bar, name, type chip, operation summary (req 13).
Rectangle {
    id: row
    signal selected()
    signal enabledToggled()
    signal viewRequested()

    readonly property bool registerOnly: model.kind === "register_write" || model.kind === "field_write"

    objectName: "actionRow_" + model.name
    width: ListView.view ? ListView.view.width : 600
    height: 36
    color: model.current ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")

    HoverHandler { id: hover }
    TapHandler {
        onTapped: row.selected()
        onDoubleTapped: row.viewRequested()
    }

    Rectangle {
        width: 3
        height: parent.height - 12
        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        radius: 2
        color: Theme.kindColor(model.kind)
        visible: !row.registerOnly
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s2

        AppCheckBox {
            objectName: "actionEnabled_" + model.name
            accessibleName: "Include " + model.name + " in Run checked"
            checked: model.enabled
            onClicked: row.enabledToggled()
        }
        Text {
            text: model.name
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Chip {
            visible: !row.registerOnly
            text: model.kind.replace(/_/g, " ")
            accent: Theme.kindColor(model.kind)
        }
        Text {
            text: model.opsText.split(" · ")[0]
            font.family: Theme.fontUi
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
