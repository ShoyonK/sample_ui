import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

TextField {
    id: control
    property bool mono: false
    property string leadingIcon: ""
    property bool selectOnFocus: false  // numeric settings: click in and type to replace
    property bool invalid: false        // red border (e.g. req 32 input validation)

    onActiveFocusChanged: if (activeFocus && selectOnFocus) selectAll()

    implicitHeight: 28
    leftPadding: leadingIcon !== "" ? 28 : 9
    rightPadding: 9
    topPadding: 0
    bottomPadding: 0
    verticalAlignment: TextInput.AlignVCenter
    font.family: mono ? Theme.fontMono : Theme.fontUi
    font.pixelSize: mono ? Theme.fontMd : Theme.fontSm
    color: Theme.textPrimary
    placeholderTextColor: Theme.textMuted
    selectionColor: Theme.infoFg
    selectedTextColor: "#FFFFFF"
    selectByMouse: true

    background: Rectangle {
        radius: Theme.radiusSm
        color: control.enabled ? Theme.surface : Theme.surface2
        border.width: 1
        border.color: control.invalid ? Theme.dangerFg : control.activeFocus ? Theme.textPrimary : Theme.borderStrong
        Icon {
            visible: control.leadingIcon !== ""
            name: control.leadingIcon
            size: 13
            anchors.left: parent.left
            anchors.leftMargin: 9
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
