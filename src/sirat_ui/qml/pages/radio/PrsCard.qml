import QtQuick 2.15
import "../../theme"

PrsCardForm {
    readonly property var vm: app.prs

    sourceLabel.text: vm.sourceText
    signalCombo.model: vm.signalLabels
    signalCombo.currentIndex: vm.signalIndex
    signalCombo.onActivated: vm.setSignal(index)
    pinCombo.model: vm.pins
    pinCombo.currentIndex: vm.pinIndex
    pinCombo.onActivated: vm.setPin(index)
    channelCombo.model: vm.channels
    channelCombo.currentIndex: vm.channelIndex
    channelCombo.onActivated: vm.setChannel(index)
    hintLabel.text: vm.hint + ". " + vm.constraintText
    hintLabel.color: vm.invalid ? Theme.warnFg : Theme.textMuted
    applyButton.enabled: vm.canRoute
    applyButton.onClicked: vm.apply()
    addButton.enabled: vm.signalIndex >= 0
    addButton.onClicked: vm.addToActions()
    routeList.model: vm.routes
    routeList.delegate: PrsRouteRow {
        onRemoveRequested: vm.remove(index)
    }
    routesEmpty.visible: routeList.count === 0
}
