import QtQuick 2.15

SettingsPageForm {
    readonly property var vm: app.settings

    darkModeBox.checked: vm.darkMode
    darkModeBox.onClicked: vm.setDarkMode(darkModeBox.checked)
    autoReadBox.checked: vm.autoRead
    autoReadBox.onClicked: vm.setAutoRead(autoReadBox.checked)
    confirmBox.checked: vm.confirmCritical
    confirmBox.onClicked: vm.setConfirmCritical(confirmBox.checked)
    secureBox.checked: vm.showSecure
    secureBox.onClicked: vm.setShowSecure(secureBox.checked)
    clearCacheButton.onClicked: vm.clearRegisterCache()
    exportButton.onClicked: vm.exportSettings()
    importButton.onClicked: vm.importSettings()
    clearAllButton.onClicked: vm.clearAllSettings()
    aboutGrid.rows: vm.aboutRows
    saveSessionButton.onClicked: app.sessions.saveSession()
    loadSessionButton.onClicked: app.sessions.openBrowser()
    autosaveLabel.text: app.sessions.autosaveText
}
