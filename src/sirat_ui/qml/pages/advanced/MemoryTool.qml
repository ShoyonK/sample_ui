import QtQuick 2.15

MemoryToolForm {
    id: tool
    readonly property var vm: app.memory

    addressField.text: vm.address
    addressField.invalid: !!vm.errors.address
    addressField.onTextEdited: vm.setField("address", addressField.text)
    addressField.onAccepted: vm.read()
    sizeField.text: vm.size
    sizeField.invalid: !!vm.errors.size
    sizeField.onTextEdited: vm.setField("size", sizeField.text)
    sizeField.onAccepted: vm.read()
    formatControl.model: vm.formats
    formatControl.currentIndex: vm.formatIndex
    formatControl.onActivated: vm.setFormat(index)
    readButton.enabled: vm.canRead
    readButton.busy: vm.busy
    readButton.onClicked: vm.read()
    readError.text: vm.errors.address || vm.errors.size || ""
    copyButton.enabled: vm.hasData
    copyButton.onClicked: vm.copyDump()
    headerLabel.text: vm.headerText
    headerLabel.visible: vm.hasData
    dumpList.model: vm.rows
    dumpList.delegate: MemoryRow {
        onAddressClicked: tool.vm.useRowAddress(index)
    }
    emptyState.visible: !vm.hasData
    emptyState.body: vm.emptyText
    writeAddressField.text: vm.writeAddress
    writeAddressField.onTextEdited: vm.setField("writeAddress", writeAddressField.text)
    writeValueField.text: vm.writeValue
    writeValueField.onTextEdited: vm.setField("writeValue", writeValueField.text)
    writeValueField.invalid: !!vm.errors.write
    writeSizeControl.model: vm.writeSizes
    writeSizeControl.currentIndex: vm.writeSizeIndex
    writeSizeControl.onActivated: vm.setWriteSize(index)
    writeButton.enabled: vm.canWrite
    writeButton.onClicked: vm.write()
    writeError.text: vm.errors.write || ""
}
