import QtQuick 2.15
import "../../theme"

DumpsPageForm {
    readonly property var vm: app.dumps
    readonly property var result: app.comparison
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

    resultHeader.title: result.resultTitle || "Register comparison"
    saveReportButton.enabled: result.hasResult
    saveReportButton.onClicked: result.saveReport()
    clearButton.enabled: result.hasResult
    clearButton.onClicked: result.clearResult()
    summaryBanner.visible: result.hasResult
    summaryLabel.text: result.resultSummary
    summaryLabel.visible: !radio
    summaryBanner.color: radio ? Theme.surface2 : Theme.infoBg
    radioCounts.visible: radio
    matchCountLabel.text: result.matchCount + (result.matchCount === 1 ? " match" : " matches")
    mismatchCountLabel.text: result.mismatchCount + (result.mismatchCount === 1 ? " mismatch" : " mismatches")
    errorCountLabel.text: result.errorCount + (result.errorCount === 1 ? " error" : " errors")
    summaryHelp.visible: result.resultHelp !== ""
    summaryHelp.text: result.resultHelp
    readonly property bool radio: result.resultKind === "radio"
    radioButton.enabled: vm.canRead
    radioButton.onClicked: vm.openRadioDiff()
    radioHeader.visible: radio
    radioHeader.sortColumn: result.sortColumn
    radioHeader.descending: result.sortDescending
    radioHeader.onSortRequested: result.sortBy(column)
    radioList.visible: radio
    radioList.model: result.radioRows
    rowList.visible: !radio
    columnHeader.visible: result.resultKind === "registers" && rowList.count > 0
    beforeHeader.text: result.beforeLabel
    afterHeader.text: result.afterLabel
    rowList.model: result.rows
    resultEmpty.visible: rowList.count === 0
    resultEmpty.title: result.hasResult ? "No differences" : "Nothing compared yet"
    resultEmpty.body: result.hasResult ? "Every register compared has the same value on both sides."
                                   : "Pick a saved dump, then use Diff vs live to compare it with the chip, or Compare with to compare it with another dump."
}
