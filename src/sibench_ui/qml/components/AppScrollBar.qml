import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

ScrollBar {
    id: bar
    policy: ScrollBar.AsNeeded
    contentItem: Rectangle {
        implicitWidth: 6
        implicitHeight: 6
        radius: 3
        color: Theme.borderStrong
        opacity: bar.active ? 1 : 0.6
    }
}
