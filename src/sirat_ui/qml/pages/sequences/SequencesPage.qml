import QtQuick 2.15

SequencesPageForm {
    readonly property var vm: app.sequences
    readonly property bool hasSequence: vm.selectedName !== ""
    readonly property bool hasStep: vm.selectedStep >= 0
    readonly property bool editable: hasSequence && !vm.running

    newButton.onClicked: vm.newSequence()
    renameButton.enabled: editable
    renameButton.onClicked: vm.renameSequence()
    toActionsButton.enabled: hasSequence
    toActionsButton.onClicked: vm.addToActions()
    deleteButton.enabled: editable
    deleteButton.onClicked: vm.deleteSequence()
    sequenceList.model: vm.sequenceList
    sequenceList.delegate: SequenceRow {
        onActivated: vm.select(index)
    }

    titleLabel.text: vm.selectedName || "No sequence"
    statusChip.text: vm.statusText
    statusChip.tone: vm.running ? "info" : vm.statusText === "Failed" ? "danger"
                   : vm.statusText === "Finished" ? "ok" : "mute"
    codeButton.enabled: hasSequence
    codeButton.onClicked: vm.generateCode()
    runButton.text: vm.running ? "Abort" : "Run"
    runButton.iconName: vm.running ? "stop" : "play"
    runButton.variant: vm.running ? "danger" : "primary"
    runButton.enabled: vm.running || (vm.canRun && hasSequence)
    runButton.onClicked: vm.running ? vm.abort() : vm.run()
    progressBar.width: progressBar.parent.width * vm.progress
    messageLabel.text: vm.message || "Checked actions run in order on the selected DUT; unchecked ones are skipped. Stops at the first error."

    addActionButton.enabled: editable
    addActionButton.onClicked: vm.addAction()
    removeStepButton.enabled: editable && hasStep
    removeStepButton.onClicked: vm.removeSelectedStep()
    stepUpButton.enabled: editable && hasStep
    stepUpButton.onClicked: vm.moveSelectedStep(-1)
    stepDownButton.enabled: editable && hasStep
    stepDownButton.onClicked: vm.moveSelectedStep(1)
    stepList.model: vm.steps
    stepList.delegate: StepRow {
        onActivated: vm.selectStep(index)
    }
    runConsole.model: vm.console
    runConsole.onClearRequested: vm.console.clear()
}
