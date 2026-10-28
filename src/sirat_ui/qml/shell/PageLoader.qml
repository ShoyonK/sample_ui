import QtQuick 2.15
import "../components"
import "PageSources.js" as PageSources

// One page slot in the main window. The page loads the first time it's opened (req 2: lazy) and stays alive.
// While the page is open in its own window it's unloaded here and a placeholder takes its place.
Item {
    id: slot
    property string key: ""
    property string title: ""
    property string currentPage: ""
    property bool visited: false
    readonly property bool poppedOut: app.windows.openKeys.indexOf("page:" + key) >= 0

    onCurrentPageChanged: if (currentPage === key) visited = true
    Component.onCompleted: if (currentPage === key) visited = true

    Loader {
        objectName: "page_" + slot.key
        anchors.fill: parent
        active: slot.visited && !slot.poppedOut
        source: PageSources.sourceFor(slot.key)
    }

    PoppedOutPlaceholder {
        objectName: "pagePlaceholder_" + slot.key
        visible: slot.poppedOut
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 520)
        title: slot.title
        onShowRequested: app.windows.show("page:" + slot.key)
        onDockRequested: app.windows.close("page:" + slot.key)
    }
}
