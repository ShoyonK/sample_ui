import QtQuick 2.15

HistoryPanelForm {
    readonly property var vm: app.history

    filterControl.checkedStates: [vm.showReads, vm.showWrites]
    filterControl.onActivated: index === 0 ? vm.toggleReads() : vm.toggleWrites()
    runButton.onClicked: vm.runSelected()
    createActionButton.onClicked: vm.createAction()
    codeButton.onClicked: vm.generateCode()
    copyButton.onClicked: vm.copyAll()
    clearButton.onClicked: vm.clear()
    list.model: vm.model
    list.delegate: HistoryRow {
        onClicked: vm.select(index, mode)
        onSaveRequested: vm.saveSelected()
    }
}
