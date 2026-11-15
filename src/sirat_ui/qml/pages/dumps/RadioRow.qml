import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 21 colors: a mismatch row is tinted red and an error row orange, with an edge in the same color, so
// problems stand out; matches stay plain (green on the Status cell). Rows come sorted with mismatches first.
Rectangle {
    id: row
    property var widths   // RadioHeader's column widths
    readonly property string tone: model.status === "match" ? "ok" : model.status === "mismatch" ? "danger" : "warn"
    readonly property bool problem: model.status !== "match"

    objectName: "radio_" + model.peripheral + "." + model.register + "." + model.field
    width: ListView.view ? ListView.view.width : 1000
    height: 32
    color: problem ? Theme.toneBg(tone) : Theme.surface

    Rectangle {
        visible: row.problem
        width: 3
        height: parent.height
        color: Theme.toneFg(row.tone)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Text { text: model.peripheral; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: row.widths.peripheral }
        Text { text: model.register; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: row.widths.register }
        Text { text: model.field; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: row.widths.field }
        Text { text: model.expected; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: row.widths.expected }
        Text { text: model.actual; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: model.status === "mismatch" ? Font.DemiBold : Font.Normal; color: model.status === "mismatch" ? Theme.dangerFg : Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: row.widths.actual }
        RowLayout {
            spacing: 6
            Layout.fillWidth: true
            Icon {
                name: model.status === "match" ? "check" : model.status === "mismatch" ? "warning" : "close"
                size: 12
                color: Theme.toneFg(row.tone)
            }
            Text { text: model.statusText; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.toneFg(row.tone); Layout.fillWidth: true }
        }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
}
