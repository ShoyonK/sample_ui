import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

RowLayout {
    property string title: ""
    property string message: ""
    property string iconName: "warning"
    property string tone: "warn"
    spacing: Theme.s3

    Rectangle {
        Layout.alignment: Qt.AlignTop
        width: 36
        height: 36
        radius: Theme.radius
        color: Theme.toneBg(parent.tone)
        Icon {
            anchors.centerIn: parent
            name: parent.parent.iconName
            size: 17
            color: Theme.toneFg(parent.parent.tone)
        }
    }
    ColumnLayout {
        spacing: 4
        Layout.fillWidth: true
        Text {
            text: parent.parent.title
            font.pixelSize: Theme.fontHeading
            font.weight: Font.DemiBold
            color: Theme.textPrimary
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Text {
            text: parent.parent.message
            visible: text !== ""
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}
