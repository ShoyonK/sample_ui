import QtQuick 2.15

DumpsPageForm {
    readonly property var vm: app.dumps
    readonly property bool hasDump: vm.selectedPath !== ""

    folderHeader.meta: vm.folder
    takeButton.enabled: vm.canRead
    takeButton.onClicked: vm.openPicker()
    fileList.model: vm.files
    fileList.delegate: DumpFileRow {
        onActivated: vm.select(index)
    }
    filesEmpty.visible: fileList.count === 0
    diffLiveButton.enabled: hasDump && vm.canRead
    diffLiveButton.onClicked: vm.diffLive()
    compareWithButton.enabled: hasDump && fileList.count > 1
    compareWithButton.onClicked: vm.compareWith()
    compareFilesButton.onClicked: vm.compareFiles()
    deleteButton.enabled: hasDump
    deleteButton.onClicked: vm.deleteSelected()

    resultHeader.title: vm.resultTitle || "Register comparison"
    saveReportButton.enabled: vm.hasResult
    saveReportButton.onClicked: vm.saveReport()
    clearButton.enabled: vm.hasResult
    clearButton.onClicked: vm.clearResult()
    summaryBanner.visible: vm.hasResult
    summaryLabel.text: vm.resultSummary
    summaryHelp.visible: vm.resultHelp !== ""
    summaryHelp.text: vm.resultHelp
    readonly property bool radio: vm.resultKind === "radio"
    radioButton.enabled: vm.canRead
    radioButton.onClicked: vm.openRadioDiff()
    radioHeader.visible: radio
    radioHeader.sortColumn: vm.sortColumn
    radioHeader.descending: vm.sortDescending
    radioHeader.onSortRequested: vm.sortBy(column)
    radioList.visible: radio
    radioList.model: vm.radioRows
    rowList.visible: !radio
    columnHeader.visible: vm.resultKind === "registers" && rowList.count > 0
    beforeHeader.text: vm.beforeLabel
    afterHeader.text: vm.afterLabel
    rowList.model: vm.rows
    resultEmpty.visible: rowList.count === 0
    resultEmpty.title: vm.hasResult ? "No differences" : "Nothing compared yet"
    resultEmpty.body: vm.hasResult ? "Every register compared has the same value on both sides."
                                   : "Pick a saved dump, then use Diff vs live to compare it with the chip, or Compare with to compare it with another dump."
}
