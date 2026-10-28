import QtQuick 2.15

BlePacketCardForm {
    readonly property var vm: app.blePacket

    accessField.text: vm.accessAddress
    accessField.onTextEdited: vm.setField("accessAddress", accessField.text)
    accessField.invalid: !!vm.errors.accessAddress
    crcField.text: vm.crcInit
    crcField.onTextEdited: vm.setField("crcInit", crcField.text)
    crcField.invalid: !!vm.errors.crcInit
    whiteningField.text: vm.whitening
    whiteningField.onTextEdited: vm.setField("whitening", whiteningField.text)
    whiteningField.invalid: !!vm.errors.whitening
    preambleField.text: vm.preamble
    preambleField.onTextEdited: vm.setField("preamble", preambleField.text)
    preambleField.invalid: !!vm.errors.preamble
    syncLabel.text: vm.syncWord
    errorLabel.text: vm.errorText
    generateButton.enabled: vm.canGenerate
    generateButton.onClicked: vm.generateCode()
}
