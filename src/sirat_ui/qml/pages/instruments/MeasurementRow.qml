import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"

// One channel's timing measurements in the ECA analysis table.
Rectangle {
    objectName: "ecaMeasure_" + model.channel
    width: ListView.view ? ListView.view.width : 800
    height: 30
    color: index % 2 ? Theme.surface2 : "transparent"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Text { text: model.channel; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; Layout.preferredWidth: 90 }
        Text { text: model.range; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.fillWidth: true }
        Text { text: model.mean; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 80 }
        Text { text: model.edges; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 90 }
        Text { text: model.frequency; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 90 }
        Text { text: model.highTime; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 90 }
        Text { text: model.firstRise; font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; Layout.preferredWidth: 90 }
    }
}
