import QtQuick 2.15

LogPanelForm {
    id: panel
    readonly property var vm: app.log
    property bool inWindow: false

    levelControl.model: vm.levelLabels
    levelControl.checkedStates: vm.levelStates
    levelControl.onActivated: vm.toggleLevel(index)
    searchField.onTextEdited: vm.setSearchText(searchField.text)
    searchField.onAccepted: vm.nextMatch()
    matchLabel.text: vm.matchText
    previousButton.enabled: vm.matchText !== "" && vm.matchText !== "no matches"
    previousButton.onClicked: vm.previousMatch()
    nextButton.enabled: previousButton.enabled
    nextButton.onClicked: vm.nextMatch()
    saveButton.onClicked: vm.saveLog()
    clearButton.onClicked: vm.clear()
    popOutButton.visible: !inWindow
    popOutButton.onClicked: vm.setPoppedOut(true)
    hideButton.visible: !inWindow
    hideButton.onClicked: app.dock.toggle()
    hideButton.tip: "Hide panels · " + app.palette.shortcutMap["toggle_dock"]
    list.model: vm.model
    // Follow new lines unless the user is searching.
    list.onCountChanged: if (vm.searchText === "") list.positionViewAtEnd()

    Connections {
        target: panel.vm
        function onCurrentMatchMoved(row) {
            panel.list.positionViewAtIndex(row, ListView.Center)
        }
    }
}
