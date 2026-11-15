import QtQuick 2.15

LpwPhyCardForm {
    readonly property var vm: app.lpwPhy

    currentChip.text: "PHY: " + (vm.currentPhy || "none")
    currentChip.tone: vm.currentPhy ? "ok" : "mute"
    phyField.text: vm.phyName
    phyField.onTextEdited: vm.setPhyName(phyField.text)
    phyField.onAccepted: if (loadButton.enabled) vm.load()
    knownCombo.model: vm.knownPhys
    knownCombo.onActivated: vm.setPhyName(vm.knownPhys[index])
    browseButton.onClicked: vm.browse()
    loadButton.text: vm.busy ? "Loading…" : "Load PHY"
    loadButton.enabled: vm.canLoad && vm.phyName !== ""
    loadButton.onClicked: vm.load()
    addButton.enabled: vm.phyName !== ""
    addButton.onClicked: vm.addToActions()
}
