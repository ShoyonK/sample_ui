import QtQuick 2.15
import "../theme"

// levels: ok, danger, warn, busy, info
Rectangle {
    id: root
    property string text: ""
    property string level: "ok"
    property bool compact: false

    implicitWidth: row.implicitWidth + 20
    implicitHeight: compact ? 22 : 26
    radius: height / 2
    color: "transparent"
    border.color: Theme.border

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            width: 7; height: 7; radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: root.level === "ok" ? Theme.okFg
                 : root.level === "danger" ? Theme.dangerFg
                 : root.level === "busy" ? Theme.infoFg : Theme.warnFg
            SequentialAnimation on opacity {
                running: root.level === "busy"
                loops: Animation.Infinite
                alwaysRunToEnd: true
                NumberAnimation { to: 0.25; duration: 500 }
                NumberAnimation { to: 1; duration: 500 }
            }
        }
        Text {
            text: root.text
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontSm
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
