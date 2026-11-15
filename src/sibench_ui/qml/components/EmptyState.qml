import QtQuick 2.15
import "../theme"

Column {
    id: root
    property string iconName: "info"
    property string title: ""
    property string body: ""
    spacing: Theme.s2
    width: Math.min(parent ? parent.width - 2 * Theme.s6 : 320, 420)

    Icon {
        name: root.iconName
        size: 28
        anchors.horizontalCenter: parent.horizontalCenter
    }
    Text {
        text: root.title
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        font.family: Theme.fontUi
        font.pixelSize: Theme.fontLg
        font.weight: Font.DemiBold
        color: Theme.textPrimary
        wrapMode: Text.WordWrap
    }
    Text {
        text: root.body
        visible: text !== ""
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        font.family: Theme.fontUi
        font.pixelSize: Theme.fontSm
        color: Theme.textMuted
        wrapMode: Text.WordWrap
    }
}
