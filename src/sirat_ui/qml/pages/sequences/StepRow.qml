import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One action in a sequence. The action currently executing is highlighted yellow (req 14).
Rectangle {
    id: row
    signal activated()

    readonly property bool inactive: model.state === "skipped" || model.state === "missing"

    objectName: "step_" + model.title
    width: ListView.view ? ListView.view.width : 1000
    height: 48
    color: model.state === "running" ? Theme.changed
         : model.selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
    Behavior on color { ColorAnimation { duration: 150 } }
    HoverHandler { id: hover }
    TapHandler { onTapped: row.activated() }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 10
        opacity: row.inactive ? 0.55 : 1

        Text {
            text: model.num
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            Layout.preferredWidth: 24
        }
        Item {
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            Rectangle {
                anchors.centerIn: parent
                width: 14
                height: 14
                radius: 7
                color: model.state === "done" ? Theme.okFg : model.state === "failed" ? Theme.dangerFg : "transparent"
                border.width: 1.5
                border.color: model.state === "running" ? Theme.infoFg
                            : model.state === "missing" ? Theme.warnFg
                            : (model.state === "pending" || model.state === "skipped") ? Theme.borderStrong : color
                Icon {
                    anchors.centerIn: parent
                    visible: model.state === "done" || model.state === "failed"
                    name: model.state === "done" ? "check" : "close"
                    size: 8
                    color: Theme.surface
                }
                RotationAnimation on rotation {
                    running: model.state === "running"
                    from: 0; to: 360; duration: 1200; loops: Animation.Infinite
                }
            }
        }
        Column {
            Layout.fillWidth: true
            spacing: 2
            Text {
                text: model.title
                width: parent.width
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontMd
                font.strikeout: model.state === "missing"
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
            Text {
                text: model.detail
                width: parent.width
                font.pixelSize: Theme.fontXs
                color: model.state === "missing" ? Theme.warnFg : Theme.textMuted
                elide: Text.ElideRight
            }
        }
        Chip {
            text: model.state === "skipped" ? "skipped" : model.state === "missing" ? "missing" : model.kind
            tone: model.state === "missing" ? "warn" : "mute"
            accent: row.inactive ? "transparent" : Theme.kindColor(model.kind)
        }
        Text {
            text: model.durationText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: 52
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
