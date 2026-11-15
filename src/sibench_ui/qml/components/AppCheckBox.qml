import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

CheckBox {
    id: control
    spacing: Theme.s2
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
        readonly property bool partial: control.checkState === Qt.PartiallyChecked
        color: control.checked || partial ? Theme.checkOn : (control.hovered ? Theme.bitHover : Theme.surface)
        border.color: control.visualFocus ? Theme.focusRing
                    : control.checked || partial || control.hovered ? Theme.checkOnBorder : Theme.borderStrong
        border.width: control.visualFocus ? 2 : 1
        Behavior on color { ColorAnimation { duration: 120 } }
        Icon {
            anchors.centerIn: parent
            visible: control.checkState === Qt.Checked
            name: "check"
            size: 10
            color: Theme.checkMark
        }
        Rectangle {   // some, not all (a tristate box)
            anchors.centerIn: parent
            visible: parent.partial
            width: 8
            height: 2
            radius: 1
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
