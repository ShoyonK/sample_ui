import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// A themed context menu. Fill it with AppMenuItem.
Menu {
    id: menu
    padding: 4
    background: Rectangle {
        implicitWidth: 230
        radius: Theme.radius
        color: Theme.surface
        border.color: Theme.borderStrong
    }
}
