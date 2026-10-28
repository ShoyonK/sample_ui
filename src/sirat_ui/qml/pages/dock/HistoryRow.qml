import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Click selects; Ctrl+click toggles; Shift+click selects a range (req 9). Right-click: Save selected.
Rectangle {
    id: row
    signal clicked(string mode)
    signal saveRequested()

    objectName: "historyRow_" + index
    width: ListView.view ? ListView.view.width : 600
    height: 34
    color: model.selected ? Theme.select : (area.containsMouse ? Theme.surface2 : "transparent")

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: {
            if (mouse.button === Qt.RightButton) {
                if (!model.selected)
                    row.clicked("single")
                menu.popup()
                return
            }
            row.clicked((mouse.modifiers & Qt.ShiftModifier) ? "range"
                        : (mouse.modifiers & Qt.ControlModifier) ? "toggle" : "single")
        }
    }
    Menu {
        id: menu
        MenuItem {
            text: "Save selected…"
            onTriggered: row.saveRequested()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s2

        Text {
            text: model.time
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            Layout.preferredWidth: 64
        }
        // req 9 colors: READ blue, register WRITE green, field WRITE yellow
        Chip {
            text: model.operation
            tone: model.kind === "field_write" ? "warn" : model.kind === "write" ? "ok" : "info"
            Layout.preferredWidth: 54
        }
        Text {
            text: model.target
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: model.valueText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textPrimary
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
