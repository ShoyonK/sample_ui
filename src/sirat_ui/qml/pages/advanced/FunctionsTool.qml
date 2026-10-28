import QtQuick 2.15
import "../../theme"

FunctionsToolForm {
    id: tool
    readonly property var vm: app.customFunctions

    functionList.model: vm.functions
    functionList.currentIndex: vm.selectedIndex
    functionList.delegate: FunctionRow {
        selected: index === tool.vm.selectedIndex
        onActivated: tool.vm.select(index)
    }
    listEmpty.visible: functionList.count === 0
    newButton.onClicked: vm.newFunction()
    renameButton.enabled: vm.hasSelection
    renameButton.onClicked: vm.renameFunction()
    deleteButton.enabled: vm.hasSelection
    deleteButton.onClicked: vm.deleteFunction()
    editorHeader.title: vm.selectedName
    editorHeader.visible: vm.hasSelection
    addButton.enabled: vm.hasSelection
    addButton.onClicked: vm.addToActions()
    runButton.enabled: vm.canRun
    runButton.busy: vm.running
    runButton.onClicked: vm.run()
    editor.visible: vm.hasSelection
    editor.code: vm.code
    editor.placeholder: vm.placeholder
    editor.onEdited: vm.setCode(text)
    editor.onRunRequested: vm.run()
    editor.onDocumentReady: vm.attachHighlighter(doc, Theme.dark)
    runHint.text: vm.runHint
    runHint.visible: vm.hasSelection
    output.model: vm.output
    output.visible: vm.hasSelection
    noSelection.visible: !vm.hasSelection

    Connections {
        target: Theme
        function onDarkChanged() { tool.vm.attachHighlighter(tool.editor.editor.textDocument, Theme.dark) }
    }
}
