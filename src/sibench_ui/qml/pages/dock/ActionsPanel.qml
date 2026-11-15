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
    runSelectedButton.tip: "Run the checked actions · " + app.palette.shortcutMap["run_checked"]
    codeButton.onClicked: vm.generateCode()
    upButton.enabled: hasCurrent
    upButton.onClicked: vm.moveCurrent(-1)
    downButton.enabled: hasCurrent
    downButton.onClicked: vm.moveCurrent(1)
    allBox.checkState: vm.total > 0 && vm.checkedCount === vm.total ? Qt.Checked
                     : vm.checkedCount > 0 ? Qt.PartiallyChecked : Qt.Unchecked
    allBox.nextCheckState: function() { return allBox.checkState }   // the ViewModel decides; the box follows it
    allBox.enabled: vm.total > 0
    allBox.onClicked: vm.setAllChecked(vm.checkedCount < vm.total)
    checkedLabel.text: vm.total === 0 ? "No actions" : vm.checkedCount + " of " + vm.total + " checked"
    dockTools.visible: !showManagement
    dockUpButton.enabled: hasCurrent
    dockUpButton.onClicked: vm.moveCurrent(-1)
    dockDownButton.enabled: hasCurrent
    dockDownButton.onClicked: vm.moveCurrent(1)
    dockDeleteButton.enabled: vm.selectedCount > 0
    dockDeleteButton.tip: vm.selectedCount > 1 ? "Delete the " + vm.selectedCount + " selected actions"
                                               : "Delete the selected action · Ctrl or Shift+click selects more"
    dockDeleteButton.onClicked: vm.removeSelected()
    dockDeleteAllButton.enabled: vm.total > 0
    dockDeleteAllButton.onClicked: vm.removeAll()
    addToSequenceButton.onClicked: vm.addCheckedToSequence()
    deleteButton.enabled: vm.selectedCount > 0
    deleteButton.text: vm.selectedCount > 1 ? "Delete " + vm.selectedCount : "Delete"
    deleteButton.onClicked: vm.removeSelected()
    deleteAllButton.onClicked: vm.removeAll()
    runConsole.model: vm.console
    runConsole.onClearRequested: vm.console.clear()
    list.model: vm.model
    list.delegate: ActionRow {
        onSelected: vm.selectRow(index, mode)
        onEnabledToggled: vm.toggleEnabled(index)
        onViewRequested: {
            vm.select(index)
            vm.viewCurrent()
        }
    }
}
