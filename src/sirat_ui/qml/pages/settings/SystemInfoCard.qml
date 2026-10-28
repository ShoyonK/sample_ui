import QtQuick 2.15

SystemInfoCardForm {
    readonly property var vm: app.systemInfo

    tabs.model: vm.tabTitles
    tabs.currentIndex: vm.tabIndex
    tabs.onActivated: vm.setTabIndex(index)
    grid.rows: vm.currentRows
    grid.visible: vm.currentRows.length > 0
    statusLabel.text: vm.statusText
    refreshButton.busy: vm.busy
    refreshButton.onClicked: vm.refresh()
    copyButton.onClicked: vm.copyAll()
}
