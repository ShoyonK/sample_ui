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
    livePill.text: vm.live ? "Live" : "Paused"
    livePill.level: vm.live ? "ok" : "warn"
    liveButton.text: vm.live ? "Pause" : "Start"
    liveButton.iconName: vm.live ? "pause" : "play"
    liveButton.onClicked: vm.toggleLive()
    refreshButton.onClicked: vm.refreshOnce()
    addAllButton.onClicked: vm.addAllToLogger()
    addSelectedButton.enabled: vm.selectedCount > 0
    addSelectedButton.onClicked: vm.addSelectedToLogger()
    deleteSelectedButton.enabled: vm.selectedCount > 0
    deleteSelectedButton.onClicked: vm.removeSelected()
    clearButton.onClicked: vm.clearAll()
    popOutButton.visible: !inWindow
    popOutButton.onClicked: app.windows.open("watchList", "")
    emptyState.visible: list.count === 0
    list.model: vm.model
    list.delegate: WatchRow {
        onRemoveRequested: vm.remove(index)
        onClicked: vm.select(index, mode)
        onWriteRequested: vm.writeValue(index)
        onLoggerRequested: vm.addRowToLogger(index)
    }
}
