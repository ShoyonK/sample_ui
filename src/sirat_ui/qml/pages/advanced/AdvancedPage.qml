import QtQuick 2.15

// Each tool binds its own ViewModel (app.pyConsole, app.customFunctions, app.dutControl, app.memory).
AdvancedPageForm {
    readonly property var vm: app.advanced

    tabs.model: vm.tabs
    tabs.currentIndex: vm.tab
    tabs.onActivated: vm.setTab(index)
    stack.currentIndex: vm.tab
}
