import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Alerts such as "Write verification failed".
ModalDialog {
    id: dialog
    objectName: "alertDialog"
    readonly property var vm: app.dialogs
    readonly property var req: vm.alert

    visible: req.title !== undefined
    dialogWidth: 460

    contentItem: ColumnLayout {
        spacing: 14
        DialogHeader {
            title: dialog.req.title || ""
            message: dialog.req.message || ""
            iconName: dialog.req.level === "info" ? "info" : "warning"
            tone: dialog.req.level === "info" ? "info" : "warn"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            Item { Layout.fillWidth: true }
            AppButton {
                objectName: "alertOkButton"
                text: "OK"
                variant: "primary"
                onClicked: dialog.vm.dismissAlert()
            }
        }
    }
}
