import QtQuick 2.15
import "../../theme"

RegisterDetailForm {
    readonly property var vm: app.detail

    mode: vm.mode
    titleLabel.text: vm.title
    favoriteButton.iconName: vm.isFavorite ? "starFilled" : "star"
    favoriteButton.tip: vm.isFavorite ? "Remove from favorites" : "Add to favorites"
    favoriteButton.onClicked: vm.toggleFavorite()
    accessChip.text: vm.accessText
    accessChip.tone: Theme.accessTone(vm.accessKey)
    metaLabel.text: vm.metaText
    chipLabel.text: vm.chipShort
    descriptionLabel.text: vm.description

    valueField.text: vm.valueText
    valueField.enabled: vm.canWrite || vm.canRead
    valueField.onAccepted: vm.write(valueField.text)
    formatControl.currentIndex: vm.formatIndex
    formatControl.onActivated: vm.setFormatIndex(index)
    readButton.enabled: vm.canRead && !vm.busy
    readButton.busy: vm.busy
    readButton.onClicked: vm.read()
    writeButton.enabled: vm.canWrite && !vm.busy
    writeButton.onClicked: vm.write(valueField.text)

    bitValueLabel.text: vm.hasValue ? vm.valueText : "not read"
    bitGrid.bitValues: vm.bitValues
    bitGrid.fieldBits: vm.fieldBits
    bitGrid.interactive: vm.canWrite && vm.hasValue
    bitGrid.onBitClicked: vm.toggleBit(bit)

    fieldsCountChip.text: vm.fieldCount + (vm.fieldCount === 1 ? " field" : " fields")
    fieldsTable.model: vm.fields
    fieldsTable.showCalculated: vm.showCalculated
    fieldsTable.onValueEdited: vm.setFieldValue(row, text)
    fieldsTable.onNoteEdited: vm.setNote(row, text)
    fieldsTable.onWatchClicked: vm.addToWatch(row)
    fieldsTable.onLoggerClicked: vm.addToLogger(row)
    fieldsTable.onFormulaClicked: vm.editFormula(row)
    saveActionButton.enabled: vm.hasValue
    saveActionButton.onClicked: vm.saveToActions()

    peripheralTitle.text: vm.title
    peripheralBody.text: vm.description + " · " + vm.registerCount + " registers"
    readPeripheralButton.enabled: vm.canRead && !app.readAll.isOpen
    readPeripheralButton.onClicked: vm.readPeripheral()
}
