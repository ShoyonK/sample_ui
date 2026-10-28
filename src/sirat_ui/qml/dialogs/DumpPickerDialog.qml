import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 12 "Select Peripherals to Dump" and req 21 "Select Peripherals for Comparison": a checkbox per
// peripheral (with its register or field count), Select All / Select None, Dump or Compare / Cancel.
ModalDialog {
    id: dialog
    objectName: "dumpPicker"
    readonly property var vm: app.dumps

    visible: vm.pickerOpen
    dialogWidth: 440

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: dialog.vm.pickerTitle
            message: dialog.vm.pickerMessage
            iconName: "download"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        RowLayout {
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            spacing: 6
            AppButton { objectName: "dumpSelectAllButton"; text: "Select all"; small: true; onClicked: dialog.vm.selectAll() }
            AppButton { objectName: "dumpSelectNoneButton"; text: "Select none"; small: true; onClicked: dialog.vm.selectNone() }
            Item { Layout.fillWidth: true }
            Text {
                text: dialog.vm.checkedCount + " selected"
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.preferredHeight: 380
            radius: Theme.radius
            color: Theme.surface
            border.color: Theme.border
            clip: true
            ListView {
                objectName: "dumpPeripheralList"
                anchors.fill: parent
                anchors.margins: 1
                model: dialog.vm.peripherals
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: Item {
                    width: ListView.view ? ListView.view.width : 380
                    height: 32
                    AppCheckBox {
                        objectName: "dumpPeripheral_" + model.name
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.label
                        checked: model.checked
                        onClicked: dialog.vm.togglePeripheral(index)
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            spacing: Theme.s2
            Item { Layout.fillWidth: true }
            AppButton { objectName: "dumpPickerCancelButton"; text: "Cancel"; onClicked: dialog.vm.closePicker() }
            AppButton {
                objectName: "dumpStartButton"
                text: dialog.vm.pickerConfirm
                iconName: dialog.vm.pickerMode === "radio" ? "compare" : "download"
                variant: "primary"
                enabled: dialog.vm.checkedCount > 0
                onClicked: dialog.vm.startPicked()
            }
        }
    }
}
