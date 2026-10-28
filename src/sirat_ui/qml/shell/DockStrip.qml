import QtQuick 2.15
import "../theme"

DockStripForm {
    readonly property var vm: app.dock
    readonly property var levelColors: ({ error: Theme.dangerFg, warning: Theme.warnFg, success: Theme.okFg,
                                          debug: Theme.textMuted, info: Theme.infoFg })

    toggleButton.onClicked: vm.toggle()
    toggleButton.iconName: vm.collapsed ? "up" : "down"
    toggleButton.tip: (vm.collapsed ? "Show History, Actions and Log" : "Hide panels") + " · "
                      + app.palette.shortcutMap["toggle_dock"]
    historyText.text: vm.lastHistory
    historyArea.onClicked: vm.show()
    actionsText.text: vm.checkedCount === 1 ? "1 checked" : vm.checkedCount + " checked"
    actionsArea.onClicked: vm.show()
    runButton.enabled: app.actions.canRun && vm.checkedCount > 0
    runButton.onClicked: app.actions.runSelected()
    runButton.tip: "Run the checked actions · " + app.palette.shortcutMap["run_checked"]
    logText.text: vm.lastLog
    logDot.color: levelColors[vm.lastLogLevel] || Theme.infoFg
    logArea.onClicked: vm.show()
}
