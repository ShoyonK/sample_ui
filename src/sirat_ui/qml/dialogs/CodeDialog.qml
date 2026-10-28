import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 16 "Generated Python Code": highlighted code, Copy to Clipboard, Save to File..., Close.
ModalDialog {
    id: dialog
    objectName: "codeDialog"
    readonly property var vm: app.dialogs
    readonly property var req: vm.code

    visible: req.title !== undefined
    dialogWidth: 900

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: dialog.req.title || ""
            message: "Python, ready to paste into a test. Configure the DUT in the __main__ block."
            iconName: "code"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: 480
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            clip: true
            background: Rectangle { radius: Theme.radius; color: Theme.surface2; border.color: Theme.border }
            TextArea {
                objectName: "codeText"
                readOnly: true
                selectByMouse: true
                textFormat: TextEdit.RichText
                text: dialog.req.html || ""
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontSm
                padding: 12
                background: null
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            spacing: Theme.s2
            AppButton { objectName: "codeCopyButton"; text: "Copy to clipboard"; iconName: "copy"; onClicked: dialog.vm.copyCode() }
            AppButton { objectName: "codeSaveButton"; text: "Save to file…"; iconName: "save"; onClicked: dialog.vm.saveCode() }
            Item { Layout.fillWidth: true }
            AppButton { objectName: "codeCloseButton"; text: "Close"; variant: "primary"; onClicked: dialog.vm.closeCode() }
        }
    }
}
