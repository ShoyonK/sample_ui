import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Progress for register reads that take a while (req 4 Read all, req 12/21 dumps): modal, cancelable,
// "Reading PERIPHERAL.REGISTER...", X of Y. `vm` is a ReadProgressViewModel; `name` prefixes the objectNames.
ModalDialog {
    id: dialog
    property var vm
    property string name
    objectName: name + "Dialog"

    shown: vm.isOpen
    dialogWidth: 460

    contentItem: ColumnLayout {
        spacing: Theme.s3
        DialogHeader {
            title: dialog.vm.title
            message: dialog.vm.label
            iconName: "download"
            tone: "info"
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            implicitHeight: 6
            radius: 3
            color: Theme.select
            Rectangle {
                objectName: dialog.name + "Progress"
                width: parent.width * dialog.vm.progress
                height: parent.height
                radius: 3
                color: Theme.textPrimary
                Behavior on width { NumberAnimation { duration: 80 } }
            }
        }
        DialogButtons {
            Text {
                objectName: dialog.name + "Count"
                text: dialog.vm.countText
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            AppButton {
                objectName: dialog.name + "CancelButton"
                text: dialog.vm.cancelling ? "Cancelling…" : "Cancel"
                enabled: !dialog.vm.cancelling
                onClicked: dialog.vm.cancel()
            }
        }
    }
}
