import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One row of the flattened peripheral tree (Qt 5 has no QML TreeView).
Rectangle {
    id: row
    signal activated()
    signal readAllRequested()

    readonly property bool isPeripheral: model.kind === "peripheral"

    objectName: "treeRow_" + model.fullName
    width: ListView.view ? ListView.view.width : 360
    height: 26
    color: model.selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")

    HoverHandler { id: hover }
    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: row.activated()
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        enabled: row.isPeripheral
        onTapped: contextMenu.popup()
    }

    Menu {
        id: contextMenu
        MenuItem {
            text: "Read all registers"
            onTriggered: row.readAllRequested()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3 + model.depth * 18
        anchors.rightMargin: Theme.s3
        spacing: 6

        Icon {
            visible: row.isPeripheral
            name: model.expanded ? "chevronDown" : "chevronRight"
            size: 10
            Layout.preferredWidth: 12
        }
        Icon {
            visible: row.isPeripheral
            name: "box"
            size: 13
        }
        Rectangle {
            visible: !row.isPeripheral
            width: 6
            height: 6
            radius: 2
            color: Theme.toneFg(Theme.accessTone(model.access))
        }
        Text {
            text: model.name
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontMd
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: model.address
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            Layout.preferredWidth: 84
        }
        Text {
            text: model.valueText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: 80
        }
    }
}
