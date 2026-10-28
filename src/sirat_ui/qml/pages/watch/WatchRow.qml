import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../theme"
import "../../components"

// Click selects; Ctrl+click toggles; Shift+click selects a range. Double-click writes a value (req 18).
Rectangle {
    id: row
    signal removeRequested()
    signal clicked(string mode)
    signal writeRequested()
    signal loggerRequested()
    readonly property real unit: (ListView.view ? ListView.view.width : 1100) - 80

    objectName: "watchRow_" + model.name
    width: ListView.view ? ListView.view.width : 1100
    height: 38
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
        onDoubleClicked: if (mouse.button === Qt.LeftButton) row.writeRequested()
    }
    Menu {
        id: menu
        MenuItem { text: "Write value…"; enabled: model.writable; onTriggered: row.writeRequested() }
        MenuItem { text: "Add to logger"; onTriggered: row.loggerRequested() }
    }

    Row {
        x: Theme.s3
        height: parent.height

        Text {
            width: row.unit * 0.3; height: parent.height
            text: model.name
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary
        }
        Rectangle {
            width: row.unit * 0.12; height: parent.height
            color: model.changed ? Theme.changed : "transparent"
            Text {
                anchors.fill: parent
                anchors.leftMargin: 6
                text: model.valueText
                verticalAlignment: Text.AlignVCenter
                font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary
            }
        }
        Text {
            width: row.unit * 0.13; height: parent.height
            leftPadding: 6
            text: model.enumName || "—"
            verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm
            color: model.enumName ? Theme.okFg : Theme.borderStrong
        }
        Text {
            width: row.unit * 0.15; height: parent.height
            text: model.calcText || "—"
            verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm
            color: model.calcText ? Theme.infoFg : Theme.borderStrong
        }
        Text {
            width: row.unit * 0.1; height: parent.height
            text: model.changedText
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: Theme.fontSm; color: Theme.textMuted
        }
        Item {
            width: row.unit * 0.12; height: parent.height
            Sparkline {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(parent.width - 12, 110)
                height: 20
                points: model.trend
                lineColor: Theme.textMuted
                lineWidth: 1.2
            }
        }
        IconButton {
            anchors.verticalCenter: parent.verticalCenter
            objectName: "watchRemove_" + model.name
            iconName: "close"
            tip: "Remove"
            onClicked: row.removeRequested()
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
