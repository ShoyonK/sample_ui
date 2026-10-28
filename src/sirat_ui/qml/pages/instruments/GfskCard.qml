import QtQuick 2.15

GfskCardForm {
    readonly property var vm: app.gfsk

    rateField.text: vm.rate
    rateField.onTextEdited: vm.setField("rate", rateField.text)
    rateField.invalid: !!vm.errors.rate
    deviationField.text: vm.deviation
    deviationField.onTextEdited: vm.setField("deviation", deviationField.text)
    deviationField.invalid: !!vm.errors.deviation
    indexLabel.text: vm.modulationIndex
    btField.text: vm.bt
    btField.onTextEdited: vm.setField("bt", btField.text)
    btField.invalid: !!vm.errors.bt
    freqField.text: vm.frequency
    freqField.onTextEdited: vm.setField("frequency", freqField.text)
    freqField.invalid: !!vm.errors.frequency
    powerField.text: vm.power
    powerField.onTextEdited: vm.setField("power", powerField.text)
    powerField.invalid: !!vm.errors.power
    payloadCombo.model: vm.payloads
    payloadCombo.currentIndex: vm.payloadIndex
    payloadCombo.onActivated: vm.setPayload(index)
    lengthField.text: vm.length
    lengthField.onTextEdited: vm.setField("length", lengthField.text)
    lengthField.invalid: !!vm.errors.length
    errorLabel.text: vm.errorText
    generateButton.enabled: vm.canGenerate
    generateButton.onClicked: vm.generateCode()
    addButton.enabled: vm.canGenerate
    addButton.onClicked: vm.addToActions()
}
