import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

CheckBox {
    id: control
    spacing: 8
    hoverEnabled: true
    property string accessibleName: ""   // for boxes with no visible text (the action rows)
    Accessible.name: text !== "" ? text : accessibleName
    padding: 0
    font.family: Theme.fontUi
    font.pixelSize: Theme.fontSm

    indicator: Rectangle {
        implicitWidth: 16
        implicitHeight: 16
        x: control.leftPadding
        y: (control.height - height) / 2
        radius: 4
        color: control.checked ? Theme.checkOn : (control.hovered ? Theme.bitHover : Theme.surface)
        border.color: control.visualFocus ? Theme.focusRing
                    : control.checked || control.hovered ? Theme.checkOnBorder : Theme.borderStrong
        border.width: control.visualFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: 120 } }
        Icon {
            anchors.centerIn: parent
            visible: control.checked
            name: "check"
            size: 10
            color: Theme.checkMark
        }
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: Theme.textPrimary
        leftPadding: control.text !== "" ? control.indicator.width + control.spacing : control.indicator.width
        verticalAlignment: Text.AlignVCenter
    }
}
