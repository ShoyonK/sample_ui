import QtQuick 2.15
import "../components"

ModalDialog {
    id: dialog
    objectName: "confirmDialog"
    readonly property var vm: app.dialogs
    readonly property var req: vm.confirm

    visible: req.title !== undefined

    contentItem: ConfirmDialogForm {
        header.title: dialog.req.title || ""
        header.message: dialog.req.message || ""
        header.tone: dialog.req.tone === "danger" ? "danger" : "warn"
        details.rows: dialog.req.details || []
        warningBox.visible: !!dialog.req.warning
        warningLabel.text: dialog.req.warning || ""
        dontShowBox.visible: !!dialog.req.allowDontShow
        confirmButton.text: dialog.req.confirmText || "Confirm"
        confirmButton.variant: dialog.req.tone === "danger" ? "danger" : "primary"
        cancelButton.onClicked: dialog.vm.answerConfirm(false, false)
        confirmButton.onClicked: {
            dialog.vm.answerConfirm(true, dontShowBox.checked)
            dontShowBox.checked = false
        }
    }
}
