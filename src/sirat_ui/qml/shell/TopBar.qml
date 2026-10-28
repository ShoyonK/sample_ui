import QtQuick 2.15

TopBarForm {
    readonly property var appState: app.state

    chipChip.text: appState.chipLabel
    positionControl.currentIndex: appState.position - 1
    positionControl.onActivated: appState.setPosition(index + 1)
    connectionPill.text: appState.connectionText
    connectionPill.level: appState.connectionLevel
    recoverButton.visible: app.faultRecovery.hasFault
    recoverButton.busy: app.faultRecovery.busy
    recoverButton.tip: app.faultRecovery.faultText + ". Applies the safe state and clears the fault."
    recoverButton.onClicked: app.faultRecovery.recover()
    phyChip.text: appState.phyText
    themeButton.iconName: appState.darkMode ? "sun" : "moon"
    themeButton.onClicked: appState.toggleDarkMode()
    connectionButton.onClicked: app.connection.openSheet()
    searchButton.onClicked: app.palette.open()
}
