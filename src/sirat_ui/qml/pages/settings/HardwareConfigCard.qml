import QtQuick 2.15
import "../../theme"

HardwareConfigCardForm {
    readonly property var vm: app.hardware

    overrideBox.checked: vm.override
    overrideBox.onClicked: vm.setOverride(overrideBox.checked)
    hostField.enabled: vm.override
    portField.enabled: vm.override
    hostField.text: vm.host
    hostField.onTextEdited: vm.setField("host", hostField.text)
    hostField.invalid: !!vm.errors.host
    hostError.text: vm.errors.host || ""
    portField.text: vm.port
    portField.onTextEdited: vm.setField("port", portField.text)
    portField.invalid: !!vm.errors.port
    portError.text: vm.errors.port || ""
    timeoutField.text: vm.timeout
    timeoutField.onTextEdited: vm.setField("timeout", timeoutField.text)
    timeoutField.invalid: !!vm.errors.timeout
    timeoutError.text: vm.errors.timeout || ""
    positionField.text: vm.position
    positionField.onTextEdited: vm.setField("position", positionField.text)
    positionField.invalid: !!vm.errors.position
    positionError.text: vm.errors.position || ""
    saveButton.enabled: vm.canSave
    saveButton.onClicked: vm.save()
    testButton.enabled: vm.canSave
    testButton.busy: vm.busy
    testButton.onClicked: vm.testConnection()
    statusLabel.text: vm.statusText
    statusLabel.color: vm.statusLevel === "ok" ? Theme.okFg : vm.statusLevel === "danger" ? Theme.dangerFg : Theme.textMuted
}
