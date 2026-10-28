.pragma library

// Page key -> QML file, used by the main window's PageHost and by pop-out page windows.
var sources = {
    registers: "../pages/registers/RegistersPage.qml",
    watch: "../pages/watch/WatchPage.qml",
    actions: "../pages/actions/ActionsPage.qml",
    sequences: "../pages/sequences/SequencesPage.qml",
    dumps: "../pages/dumps/DumpsPage.qml",
    radio: "../pages/radio/RadioPage.qml",
    instruments: "../pages/placeholder/InstrumentsPage.qml",
    advanced: "../pages/placeholder/AdvancedPage.qml",
    tests: "../pages/placeholder/TestsPage.qml",
    settings: "../pages/settings/SettingsPage.qml"
}

function sourceFor(key) {
    return sources[key] ? Qt.resolvedUrl(sources[key]) : ""
}
