import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../components/selection.js" as Selection

// One action: checkbox (enabled), type color bar, name, type chip, operation summary (req 13).
Rectangle {
    id: row
    signal selected(string mode)   // single, toggle (Ctrl), range (Shift)
    signal enabledToggled()
    signal viewRequested()

    readonly property bool registerOnly: model.kind === "register_write" || model.kind === "field_write"

    objectName: "actionRow_" + model.name
    width: ListView.view ? ListView.view.width : 600
    height: 36
    color: model.selected ? Theme.infoBg : (hover.hovered ? Theme.surface2 : "transparent")
    Behavior on color { ColorAnimation { duration: 120 } }

    HoverHandler { id: hover }
    // Under the checkbox, so the box still takes its own clicks
    MouseArea {
        anchors.fill: parent
        onClicked: row.selected(Selection.mode(mouse.modifiers))
        onDoubleClicked: row.viewRequested()
    }
    Rectangle {   // the selection's edge, so selected rows read clearly even next to each other
        visible: model.selected
        anchors.right: parent.right
        width: 3
        height: parent.height
        color: Theme.infoFg
    }

    Rectangle {
        width: 3
        height: parent.height - 12
        anchors.left: parent.left
        anchors.leftMargin: Theme.s1
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
            color: model.selected ? Theme.infoFg : Theme.textPrimary
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
