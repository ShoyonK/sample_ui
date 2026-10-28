import QtQuick 2.15
import QtQuick.Layouts 1.15

DutControlToolForm {
    id: tool
    readonly property var vm: app.dutControl
    readonly property bool hasMethod: vm.selectedPath !== ""

    reloadButton.enabled: !vm.loading
    reloadButton.onClicked: vm.reload()
    collapseButton.onClicked: vm.collapseAll()
    filterField.text: vm.filterText
    filterField.onTextEdited: vm.setFilter(filterField.text)
    treeList.model: vm.rows
    treeList.delegate: ApiTreeRow {
        onActivated: tool.vm.activate(index)
    }
    treeEmpty.text: vm.treeText
    treeEmpty.visible: vm.treeText !== ""
    methodHeader.title: hasMethod ? vm.selectedPath : "Method"
    details.visible: hasMethod
    noMethod.visible: !hasMethod
    signatureLabel.text: vm.signature
    docLabel.text: vm.doc
    formatHint.text: vm.formatHint
    formatHint.visible: paramRepeater.count > 0
    noParams.visible: paramRepeater.count === 0
    problemLabel.text: vm.problemText
    executeButton.enabled: vm.canExecute
    executeButton.busy: vm.running
    executeButton.onClicked: vm.execute()
    addButton.enabled: hasMethod && vm.problemText === ""
    addButton.onClicked: vm.addToActions()
    output.model: vm.output

    Repeater {
        id: paramRepeater
        parent: tool.paramList
        model: tool.vm.params
        delegate: ParamRow {
            Layout.fillWidth: true
            onEdited: tool.vm.setParam(name, value)
        }
    }

    onVisibleChanged: if (visible) vm.load()
    Connections {
        target: tool.vm
        function onChanged() { if (tool.visible) tool.vm.load() }
    }
}
