import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

// Title + muted helper text on the left, actions (children) on the right.
Item {
    id: root
    property string title: ""
    property string meta: ""
    property bool monoTitle: false
    default property alias actions: actionRow.data

    implicitHeight: Theme.headerHeight

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s2

        Text {
            text: root.title
            font.family: root.monoTitle ? Theme.fontMono : Theme.fontUi
            font.pixelSize: Theme.fontMd
            font.weight: Font.DemiBold
            color: Theme.textPrimary
        }
        Text {
            text: root.meta
            visible: text !== ""
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Item { Layout.fillWidth: root.meta === "" }
        Row {
            id: actionRow
            spacing: 6
            Layout.alignment: Qt.AlignVCenter
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
