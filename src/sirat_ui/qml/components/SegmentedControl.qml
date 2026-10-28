import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// A row of mutually exclusive options. multi: each option toggles on its own (checkedStates).
Rectangle {
    id: root
    property var model: []
    property int currentIndex: 0
    property bool multi: false
    property var checkedStates: []
    property bool small: false
    signal activated(int index)

    implicitWidth: row.implicitWidth + 2
    implicitHeight: small ? 24 : 28
    radius: Theme.radiusSm
    color: Theme.surface
    border.color: Theme.borderStrong
    clip: true

    Row {
        id: row
        anchors.fill: parent
        anchors.margins: 1
        Repeater {
            model: root.model
            delegate: AbstractButton {
                id: segment
                objectName: "segment_" + modelData
                readonly property bool on: root.multi ? !!root.checkedStates[index] : index === root.currentIndex
                height: row.height
                implicitWidth: label.implicitWidth + (root.small ? 16 : 20)
                hoverEnabled: true
                onClicked: root.activated(index)
                background: Rectangle {
                    color: segment.on ? Theme.select : (segment.hovered ? Theme.surface2 : "transparent")
                    Rectangle {
                        visible: index > 0
                        width: 1
                        height: parent.height
                        color: Theme.border
                    }
                }
                contentItem: Text {
                    id: label
                    text: modelData
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: Theme.fontUi
                    font.pixelSize: root.small ? Theme.fontXs : Theme.fontSm
                    font.weight: Font.DemiBold
                    color: segment.on ? Theme.textPrimary : Theme.textMuted
                }
            }
        }
    }
}
