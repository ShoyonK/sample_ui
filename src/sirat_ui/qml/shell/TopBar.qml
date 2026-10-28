import QtQuick 2.15

TopBarForm {
    readonly property var appState: app.state

    chipChip.text: appState.chipLabel
    positionControl.currentIndex: appState.position - 1
    positionControl.onActivated: appState.setPosition(index + 1)
    connectionPill.text: appState.connectionText
    connectionPill.level: appState.connectionLevel
    phyChip.text: appState.phyText
    themeButton.iconName: appState.darkMode ? "sun" : "moon"
    themeButton.onClicked: appState.toggleDarkMode()
    connectionButton.onClicked: app.connection.openSheet()
    searchButton.onClicked: app.palette.open()
}
