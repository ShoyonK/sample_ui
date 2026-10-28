import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 13 View dialog: an action's operations, read-only; embedded code is syntax highlighted.
ModalDialog {
    id: dialog
    objectName: "actionViewDialog"
    readonly property var vm: app.actionEditor

    visible: vm.viewOpen
    dialogWidth: 700

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: dialog.vm.viewTitle
            iconName: "eye"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: 380
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            clip: true
            background: Rectangle { radius: Theme.radius; color: Theme.surface2; border.color: Theme.border }
            TextArea {
                objectName: "actionViewText"
                readOnly: true
                selectByMouse: true
                textFormat: TextEdit.RichText
                text: dialog.vm.viewHtml
                wrapMode: TextEdit.Wrap
                font.family: Theme.fontUi
                font.pixelSize: Theme.fontSm
                color: Theme.textPrimary
                padding: 12
                background: null
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            Item { Layout.fillWidth: true }
            AppButton {
                objectName: "actionViewCloseButton"
                text: "Close"
                variant: "primary"
                onClicked: dialog.vm.closeView()
            }
        }
    }
}
