import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 4 "Reading Registers": modal, cancelable, current register and X of Y.
ModalDialog {
    id: dialog
    objectName: "readAllDialog"
    readonly property var vm: app.readAll

    visible: vm.isOpen
    dialogWidth: 460

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: "Reading registers"
            message: dialog.vm.label
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
                objectName: "readAllProgress"
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
                objectName: "readAllCount"
                text: dialog.vm.countText
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            AppButton {
                objectName: "readAllCancelButton"
                text: dialog.vm.cancelling ? "Cancelling\u2026" : "Cancel"
                enabled: !dialog.vm.cancelling
                onClicked: dialog.vm.cancel()
            }
        }
    }
}
