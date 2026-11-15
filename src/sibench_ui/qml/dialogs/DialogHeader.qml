import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// A dialog's icon, title and message. Carries the dialogs' standard top and side margins.
RowLayout {
    id: root
    property string title: ""
    property string message: ""
    property string iconName: "warning"
    property string tone: "warn"
    spacing: Theme.s3
    Layout.fillWidth: true
    Layout.topMargin: 18
    Layout.leftMargin: 20
    Layout.rightMargin: 20

    Rectangle {
        Layout.alignment: Qt.AlignTop
        width: 36
        height: 36
        radius: Theme.radius
        color: Theme.toneBg(root.tone)
        Icon {
            anchors.centerIn: parent
            name: root.iconName
            size: 17
            color: Theme.toneFg(root.tone)
        }
    }
    ColumnLayout {
        spacing: Theme.s1
        Layout.fillWidth: true
        Text {
            text: root.title
            font.pixelSize: Theme.fontHeading
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Text {
            text: root.message
            visible: text !== ""
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}
