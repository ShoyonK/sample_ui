import QtQuick 2.15
import QtQml 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import "theme"
import "shell"

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 1600
    height: 950
    minimumWidth: 1180
    minimumHeight: 700
    visible: true
    title: "SiRAT — " + app.state.chipLabel
    color: Theme.canvas
    // Pop-out windows don't keep the app running once the main window is closed.
    onClosing: Qt.quit()
    font.family: Theme.fontUi
    font.pixelSize: Theme.fontMd

    Binding {
        target: Theme
        property: "dark"
        value: app.state.darkMode
    }

    AppShell {
        anchors.fill: parent
    }

    DialogHost {
        anchors.fill: parent
    }

    LogWindow { }

    // Pages, the watch list, the data logger and graphs opened in their own windows (app.windows).
    Instantiator {
        model: app.windows.model
        delegate: PopoutWindow {
            key: model.key
            kind: model.kind
            arg: model.arg
            heading: model.title
        }
    }

    Shortcut {
        sequence: "Ctrl+Q"
        onActivated: Qt.quit()
    }

    Shortcut {
        sequence: "Ctrl+K"
        context: Qt.ApplicationShortcut
        onActivated: app.palette.open()
    }
}
