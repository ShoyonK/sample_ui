import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

MenuItem {
    id: item
    property string iconName: ""

    implicitHeight: visible ? 30 : 0
    contentItem: RowLayout {
        spacing: 8
        Icon { name: item.iconName; size: 13; visible: item.iconName !== ""; color: Theme.textMuted }
        Text {
            text: item.text
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontSm
            color: item.enabled ? Theme.textPrimary : Theme.textMuted
            Layout.fillWidth: true
        }
    }
    background: Rectangle {
        radius: Theme.radiusSm
        color: item.highlighted ? Theme.select : "transparent"
    }
}
