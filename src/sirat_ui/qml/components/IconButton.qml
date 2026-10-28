import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

AbstractButton {
    id: control
    property string iconName: ""
    property string tip: ""
    property color iconColor: Theme.textMuted
    property int iconSize: 14

    hoverEnabled: true
    implicitWidth: 26
    implicitHeight: 26
    opacity: enabled ? 1 : 0.4

    contentItem: Icon {
        name: control.iconName
        size: control.iconSize
        color: control.hovered ? Theme.textPrimary : control.iconColor
    }
    background: Rectangle {
        radius: Theme.radiusSm
        color: control.hovered ? Theme.select : "transparent"
    }

    ToolTip.visible: hovered && tip !== ""
    ToolTip.text: tip
    ToolTip.delay: 500
}
