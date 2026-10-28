import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

// Shown where a page or panel was, while it's open in its own window.
Rectangle {
    id: root
    property string title: ""
    property bool compact: false  // a short strip instead of a centered block (e.g. in place of one graph)
    signal showRequested()
    signal dockRequested()

    implicitHeight: compact ? 44 : 220
    radius: Theme.radius
    color: Theme.surface2
    border.color: Theme.border

    ColumnLayout {
        visible: !root.compact
        anchors.centerIn: parent
        spacing: Theme.s2
        width: Math.min(parent.width - 2 * Theme.s4, 420)
        Icon { name: "export"; size: 26; Layout.alignment: Qt.AlignHCenter }
        Text {
            text: root.title + " is open in its own window"
            font.pixelSize: Theme.fontMd
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Text {
            text: "Close that window, or use Bring back, to show it here again."
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Row {
            spacing: 8
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 4
            AppButton { objectName: "placeholderShow"; text: "Show window"; iconName: "export"; small: true; onClicked: root.showRequested() }
            AppButton { objectName: "placeholderDock"; text: "Bring back here"; iconName: "download"; small: true; onClicked: root.dockRequested() }
        }
    }

    RowLayout {
        visible: root.compact
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s2
        spacing: 6
        Icon { name: "export"; size: 13 }
        Text {
            text: "Open in its own window"
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        AppButton { objectName: "placeholderShowCompact"; text: "Show"; small: true; onClicked: root.showRequested() }
        AppButton { objectName: "placeholderDockCompact"; text: "Bring back"; small: true; onClicked: root.dockRequested() }
    }
}
