import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// A changed register (req 12). Rows stay neutral, like the Radio diff: the After value is in red and the
// Change cell carries the marker, so Before stays readable.
Rectangle {
    objectName: "diff_" + model.register
    width: ListView.view ? ListView.view.width : 900
    height: 34
    color: Theme.surface

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Text { text: model.register; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: 240 }
        Text { text: model.before; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 190 }
        Text { text: model.after; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.bitOnText; Layout.preferredWidth: 190 }
        RowLayout {
            spacing: 6
            Layout.fillWidth: true
            Icon { name: "warning"; size: 12; color: Theme.dangerFg }
            Text { text: model.change; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.fillWidth: true }
        }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
}
