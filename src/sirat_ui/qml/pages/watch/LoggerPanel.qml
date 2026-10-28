import QtQuick 2.15

LoggerPanelForm {
    readonly property var vm: app.logger
    property bool inWindow: false

    popOutButton.visible: !inWindow
    popOutButton.onClicked: app.windows.open("logger", "")

    statusChip.text: vm.recording ? "Recording" : "Stopped"
    statusChip.tone: vm.recording ? "ok" : "mute"
    rateField.text: vm.rateText
    // Applies on Enter or when focus leaves; a rejected value snaps back to the current rate.
    rateField.onEditingFinished: {
        vm.setRateText(rateField.text)
        rateField.text = Qt.binding(function () { return vm.rateText })
    }
    statusLabel.text: vm.statusText
    modeLabel.text: "Source: " + vm.modeText + " · drag on a plot to zoom, double-click to reset"
    resetZoomButton.visible: vm.zoomStart >= 0
    resetZoomButton.onClicked: vm.resetZoom()
    recordButton.text: vm.recording ? "Stop" : "Start"
    recordButton.iconName: vm.recording ? "stop" : "play"
    recordButton.enabled: vm.recording || vm.fieldCount > 0
    recordButton.onClicked: vm.toggleRecording()
    clearButton.onClicked: vm.clear()
    exportButton.onClicked: vm.exportCsv()
    emptyState.visible: seriesList.count === 0
    seriesList.model: vm.series
    seriesList.delegate: SeriesRow {
        xMin: vm.zoomStart
        xMax: vm.zoomEnd
        onRemoveRequested: vm.remove(index)
        onZoomRequested: vm.zoomTo(from, to)
        onResetRequested: vm.resetZoom()
    }
}
