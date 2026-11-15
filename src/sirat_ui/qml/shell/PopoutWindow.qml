import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import "../theme"
import "../components"
import "../dialogs"
import "../pages/watch"

// A page, one of its parts (the watch list, the data logger, a tool) or one graph in its own window, one per row
// of app.windows.model (which also sets the size).
// Closing it brings the content back to the main window.
Window {
    id: win
    property string key: ""
    property string kind: ""
    property string arg: ""
    property string heading: ""

    objectName: "popout_" + key
    title: "SiRAT — " + heading
    minimumWidth: 420
    minimumHeight: 300
    color: Theme.canvas
    visible: app.windows.openKeys.indexOf(win.key) >= 0   // hides as soon as it's closed; Qt destroys it later
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

    OverlayTracker { }

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
        id: toolContent
        ScrollView {   // a tool taller than its window scrolls; a card keeps its height, the Advanced tools fill
            id: scroller
            clip: true
            contentWidth: availableWidth
            contentHeight: toolLoader.height
            Loader {
                id: toolLoader
                width: scroller.availableWidth
                readonly property real natural: item ? item.implicitHeight : 0
                height: app.toolFills(win.arg) ? Math.max(scroller.availableHeight, natural) : natural
                source: Qt.resolvedUrl(app.toolSource(win.arg))
            }
        }
    }
    Component {
        id: graphContent
        GraphView { fieldName: win.arg }
    }

    Loader {
        objectName: "popoutContent_" + win.key
        anchors.fill: parent
        anchors.margins: 10
        sourceComponent: ({ page: pageContent, watchList: watchContent, logger: loggerContent,
                            tool: toolContent })[win.kind] || graphContent
    }

    ToastStack {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 20
        anchors.bottomMargin: 20
    }
}
