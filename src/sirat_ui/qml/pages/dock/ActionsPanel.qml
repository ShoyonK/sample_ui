import QtQuick 2.15

// Used in the bottom dock (compact) and on the Actions page (showManagement: true).
ActionsPanelForm {
    readonly property var vm: app.actions
    property bool showManagement: false
    readonly property bool hasCurrent: vm.currentName !== ""

    footer.visible: showManagement
    viewButton.enabled: hasCurrent
    viewButton.onClicked: vm.viewCurrent()
    editButton.enabled: hasCurrent
    editButton.onClicked: vm.editCurrent()
    runButton.enabled: vm.canRun && hasCurrent
    runSelectedButton.enabled: vm.canRun
    runButton.onClicked: vm.runCurrent()
    runSelectedButton.onClicked: vm.runSelected()
    codeButton.onClicked: vm.generateCode()
    upButton.enabled: hasCurrent
    upButton.onClicked: vm.moveCurrent(-1)
    downButton.enabled: hasCurrent
    downButton.onClicked: vm.moveCurrent(1)
    deselectAllButton.onClicked: vm.deselectAll()
    addToSequenceButton.onClicked: vm.addCheckedToSequence()
    deleteButton.enabled: hasCurrent
    deleteButton.onClicked: vm.removeCurrent()
    deleteAllButton.onClicked: vm.removeAll()
    runConsole.model: vm.console
    runConsole.onClearRequested: vm.console.clear()
    list.model: vm.model
    list.delegate: ActionRow {
        onSelected: vm.select(index)
        onEnabledToggled: vm.toggleEnabled(index)
        onViewRequested: {
            vm.select(index)
            vm.viewCurrent()
        }
    }
}
