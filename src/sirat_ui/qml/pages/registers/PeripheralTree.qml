import QtQuick 2.15

PeripheralTreeForm {
    readonly property var vm: app.tree

    searchField.onTextEdited: vm.setSearchText(searchField.text)
    searchField.onAccepted: vm.flushSearch()
    collapseButton.onClicked: vm.collapseAll()
    countLabel.text: vm.peripheralCount + " peripherals"
    list.model: vm.model
    list.delegate: TreeRow {
        onActivated: vm.activate(index)
        onReadAllRequested: vm.readAll(index)
        onDumpRequested: app.dumps.dumpPeripheral(model.fullName)
    }

    Connections {
        target: vm
        function onSearchFocusRequested() {
            searchField.forceActiveFocus()
            searchField.selectAll()
        }
    }
}
