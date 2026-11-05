import QtQuick 2.15

TestsPageForm {
    readonly property var vm: app.stationTests

    Component.onCompleted: vm.ensureLoaded()   // pages load on first visit

    testList.model: vm.catalogue
    testList.enabled: !vm.running
    testList.delegate: TestListRow {
        onToggled: vm.toggle(index)
    }
    listMessage.text: vm.emptyText
    listMessage.visible: vm.emptyText !== ""

    statusChip.visible: vm.statusText !== ""
    statusChip.text: vm.statusText
    statusChip.tone: vm.verdict === "running" ? "info" : vm.verdict === "pass" ? "ok"
                   : vm.verdict === "fail" ? "danger" : vm.verdict === "stopped" ? "warn" : "mute"
    runButton.enabled: vm.canRun
    runButton.onClicked: vm.run()
    stopButton.enabled: vm.running
    stopButton.onClicked: vm.stop()
    exportButton.enabled: vm.hasRun && !vm.running
    exportButton.onClicked: vm.exportResults()

    currentLabel.text: vm.currentText
    elapsedLabel.text: vm.elapsedText
    progressBar.width: progressBar.parent.width * vm.progress
    resultList.model: vm.results
    resultList.onCountChanged: resultList.positionViewAtEnd()   // the newest result stays in view
    resultList.delegate: TestResultRow {
        onActivated: vm.selectResult(index)
    }
    emptyResults.visible: !vm.hasRun
    output.model: vm.output
    output.title: vm.outputTitle
}
