import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 12 progress dialog: "Reading PERIPHERAL.REGISTER...", X of Y, cancelable.
ModalDialog {
    id: dialog
    objectName: "dumpProgressDialog"
    readonly property var vm: app.dumps

    visible: vm.progressOpen
    dialogWidth: 460

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: dialog.vm.progressTitle
            message: dialog.vm.progressLabel
            iconName: "download"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            implicitHeight: 6
            radius: 3
            color: Theme.select
            Rectangle {
                objectName: "dumpProgress"
                width: parent.width * dialog.vm.progress
                height: parent.height
                radius: 3
                color: Theme.textPrimary
                Behavior on width { NumberAnimation { duration: 80 } }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            Text {
                objectName: "dumpProgressCount"
                text: dialog.vm.countText
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            AppButton {
                objectName: "dumpCancelButton"
                text: dialog.vm.cancelling ? "Cancelling…" : "Cancel"
                enabled: !dialog.vm.cancelling
                onClicked: dialog.vm.cancel()
            }
        }
    }
}
