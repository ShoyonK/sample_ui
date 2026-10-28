import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 23 success dialog: configuration summary, the function called, and the TestInputs overrides applied.
ModalDialog {
    id: dialog
    objectName: "wifiResultDialog"
    readonly property var vm: app.wifiPhy

    visible: vm.resultOpen
    dialogWidth: 720

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: "WiFi PHY loaded successfully!"
            message: "The DUT is running the configuration below."
            iconName: "check"
            tone: "ok"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        KeyValueGrid {
            objectName: "wifiResultRows"
            rows: dialog.vm.resultRows
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        Text { text: "Function called"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.leftMargin: 20 }
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            implicitHeight: 34
            radius: Theme.radiusSm
            color: Theme.surface2
            Text {
                objectName: "wifiResultFunction"
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Theme.s3
                text: dialog.vm.resultFunction
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSm
                color: Theme.textPrimary
            }
        }
        Text { text: "TestInputs overrides"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.leftMargin: 20 }
        KeyValueGrid {
            objectName: "wifiOverrideRows"
            rows: dialog.vm.overrideRows
            monoValues: true
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            Item { Layout.fillWidth: true }
            AppButton { objectName: "wifiResultActionsButton"; text: "Add to Actions"; iconName: "bolt"; onClicked: dialog.vm.addToActions() }
            AppButton { objectName: "wifiResultCloseButton"; text: "Close"; variant: "primary"; onClicked: dialog.vm.closeResult() }
        }
    }
}
