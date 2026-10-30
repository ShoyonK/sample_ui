import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

AbstractButton {
    id: control
    property string iconName: ""
    property string tip: ""
    property color iconColor: Theme.textMuted
    property color iconHoverColor: Theme.textPrimary
    property int iconSize: 14
    property bool active: false   // a toggle that's on (e.g. Large values)

    hoverEnabled: true
    implicitWidth: 26
    implicitHeight: 26
    opacity: enabled ? 1 : 0.4
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.Button
    Accessible.name: tip
    Accessible.checkable: active
    Accessible.checked: active

    contentItem: Icon {
        name: control.iconName
        size: control.iconSize
        color: control.hovered || control.active ? control.iconHoverColor : control.iconColor
    }
    background: Rectangle {
        radius: Theme.radiusSm
        color: control.hovered || control.active ? Theme.select : "transparent"
        border.color: control.active ? Theme.borderStrong : "transparent"
    }

    ToolTip.visible: hovered && tip !== ""
    ToolTip.text: tip
    ToolTip.delay: 500

    // keyboard focus ring: only when focus came from the keyboard, never on mouse clicks
    Rectangle {
        z: 10
        anchors.fill: parent
        anchors.margins: -3
        radius: Theme.radiusSm + 3
        color: "transparent"
        border.width: 2
        border.color: Theme.focusRing
        visible: control.visualFocus
    }
}
