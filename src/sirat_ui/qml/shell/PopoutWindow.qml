import QtQuick 2.15
import QtQuick.Window 2.15
import "../theme"
import "../pages/watch"

// A page, the watch list, the data logger or one graph in its own window (one per row of app.windows.model).
// Closing it brings the content back to the main window.
Window {
    id: win
    property string key: ""
    property string kind: ""
    property string arg: ""
    property string heading: ""

    objectName: "popout_" + key
    title: "SiRAT — " + heading
    width: kind === "graph" ? 760 : kind === "logger" ? 560 : kind === "watchList" ? 1100 : 1400
    height: kind === "graph" ? 420 : 820
    minimumWidth: 420
    minimumHeight: 300
    color: Theme.canvas
    visible: true
    onClosing: app.windows.close(win.key)

    Connections {
        target: app.windows
        function onRaiseRequested(requested) {
            if (requested === win.key) {
                win.show()
                win.raise()
                win.requestActivate()
            }
        }
    }

    Component {
        id: pageContent
        Loader { source: Qt.resolvedUrl(app.pageSource(win.arg)) }
    }
    Component {
        id: watchContent
        WatchListPanel { inWindow: true }
    }
    Component {
        id: loggerContent
        LoggerPanel { inWindow: true }
    }
    Component {
        id: graphContent
        GraphView { fieldName: win.arg }
    }

    Loader {
        objectName: "popoutContent_" + win.key
        anchors.fill: parent
        anchors.margins: 10
        sourceComponent: win.kind === "page" ? pageContent : win.kind === "watchList" ? watchContent
                       : win.kind === "logger" ? loggerContent : graphContent
    }
}
