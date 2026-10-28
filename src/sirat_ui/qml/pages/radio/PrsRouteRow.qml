import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

Rectangle {
    id: row
    signal removeRequested()

    objectName: "prsRoute_" + model.pin
    width: ListView.view ? ListView.view.width : 500
    height: 36
    color: index % 2 ? Theme.surface2 : "transparent"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Text { text: model.signal; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; elide: Text.ElideRight; Layout.fillWidth: true }
        Text { text: model.pin; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 60 }
        Text { text: model.channel; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 90 }
        AppButton {
            objectName: "prsRemove_" + model.pin
            text: "Remove"
            iconName: "close"
            small: true
            variant: "danger"
            Layout.preferredWidth: 86
            onClicked: row.removeRequested()
        }
    }
}
