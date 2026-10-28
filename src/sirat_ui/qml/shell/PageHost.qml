import QtQuick 2.15
import QtQuick.Layouts 1.15

// One slot per page (see PageLoader); the current one is shown.
StackLayout {
    id: host
    property string currentPage: "registers"
    readonly property var keys: app.pages.map(function (p) { return p.key })
    currentIndex: Math.max(0, keys.indexOf(currentPage))

    Repeater {
        model: app.pages
        delegate: PageLoader {
            key: modelData.key
            title: modelData.title
            currentPage: host.currentPage
        }
    }
}
