import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Text prompts: action names, formulas, sequence names. Fields come from PromptRequest.
ModalDialog {
    id: dialog
    objectName: "promptDialog"
    readonly property var vm: app.dialogs
    readonly property var req: vm.prompt
    property var values: ({})

    visible: req.title !== undefined
    dialogWidth: 440
    onOpened: {
        var v = {}
        var fields = req.fields || []
        for (var i = 0; i < fields.length; i++) v[fields[i].key] = fields[i].value
        values = v
    }

    function submit() {
        vm.submitPrompt(values)
    }

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: dialog.req.title || ""
            message: dialog.req.message || ""
            iconName: "edit"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        Repeater {
            model: dialog.req.fields || []
            delegate: ColumnLayout {
                spacing: 4
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Text { text: modelData.label; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                AppComboBox {
                    visible: modelData.options && modelData.options.length > 0
                    objectName: "promptChoice_" + modelData.key
                    Layout.fillWidth: true
                    implicitHeight: 28
                    font.pixelSize: Theme.fontSm
                    model: modelData.options || []
                    currentIndex: Math.max(0, (modelData.options || []).indexOf(modelData.value))
                    onActivated: dialog.values[modelData.key] = currentText
                }
                AppTextField {
                    visible: !(modelData.options && modelData.options.length > 0)
                    objectName: "promptField_" + modelData.key
                    Layout.fillWidth: true
                    mono: modelData.key === "expr"
                    text: modelData.value
                    placeholderText: modelData.placeholder
                    focus: index === 0
                    onTextChanged: dialog.values[modelData.key] = text
                    onAccepted: dialog.submit()
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            Item { Layout.fillWidth: true }
            AppButton { objectName: "promptCancelButton"; text: "Cancel"; onClicked: dialog.vm.cancelPrompt() }
            AppButton {
                objectName: "promptSubmitButton"
                text: dialog.req.confirmText || "Save"
                variant: "primary"
                onClicked: dialog.submit()
            }
        }
    }
}
