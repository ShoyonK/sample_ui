import QtQuick 2.15

ConsoleToolForm {
    readonly property var vm: app.pyConsole

    header.meta: vm.sessionText
    helpButton.onClicked: vm.help()
    restartButton.enabled: vm.connected
    restartButton.onClicked: vm.restart()
    output.model: vm.output
    input.value: vm.draft
    input.busy: vm.busy
    input.onEdited: vm.setDraft(text)
    input.onSubmitted: vm.execute()
    input.onHistoryPrevious: vm.historyPrevious()
    input.onHistoryNext: vm.historyNext()
    executeButton.enabled: vm.draft.trim() !== "" && !vm.busy
    executeButton.busy: vm.busy
    executeButton.onClicked: vm.execute()
    onVisibleChanged: if (visible) input.field.forceActiveFocus()
}
