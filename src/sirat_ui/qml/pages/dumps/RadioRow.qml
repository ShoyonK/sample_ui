import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"

// Req 21: match rows light green, mismatches light red, errors light orange. Widths match RadioHeader.
Rectangle {
    readonly property string tone: model.status === "match" ? "ok" : model.status === "mismatch" ? "danger" : "warn"

    objectName: "radio_" + model.peripheral + "." + model.register + "." + model.field
    width: ListView.view ? ListView.view.width : 1000
    height: 32
    color: Theme.toneBg(tone)

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Text { text: model.peripheral; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: 120 }
        Text { text: model.register; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: 160 }
        Text { text: model.field; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: 170 }
        Text { text: model.expected; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: 200 }
        Text { text: model.actual; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.preferredWidth: 220 }
        Text { text: model.statusText; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.toneFg(parent.parent.tone); Layout.fillWidth: true }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.surface }
}
