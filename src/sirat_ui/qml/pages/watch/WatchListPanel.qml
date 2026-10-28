import QtQuick 2.15

WatchListPanelForm {
    readonly property var vm: app.watch
    property bool inWindow: false

    intervalField.text: vm.intervalText
    // Applies on Enter or when focus leaves; a rejected value snaps back to the current rate.
    intervalField.onEditingFinished: {
        vm.setIntervalText(intervalField.text)
        intervalField.text = Qt.binding(function () { return vm.intervalText })
    }
    // one control for one state: the lit segment is the current state, clicking the other switches
    liveToggle.currentIndex: vm.live ? 0 : 1
    liveToggle.onActivated: if ((index === 0) !== vm.live) vm.toggleLive()
    refreshButton.onClicked: vm.refreshOnce()
    densityToggle.active: vm.large
    densityToggle.onClicked: vm.setLarge(!vm.large)
    addAllButton.onClicked: vm.addAllToLogger()
    selectionGroup.visible: vm.selectedCount > 0
    selectionLabel.text: vm.selectedCount + " selected"
    addSelectedButton.onClicked: vm.addSelectedToLogger()
    deleteSelectedButton.onClicked: vm.removeSelected()
    clearButton.onClicked: vm.clearAll()
    popOutButton.visible: !inWindow
    popOutButton.onClicked: app.windows.open("watchList", "")
    emptyState.visible: list.count === 0
    list.model: vm.model
    list.delegate: WatchRow {
        large: vm.large
        onRemoveRequested: vm.remove(index)
        onClicked: vm.select(index, mode)
        onWriteRequested: vm.writeValue(index)
        onLoggerRequested: vm.addRowToLogger(index)
    }
}
