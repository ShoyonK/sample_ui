import QtQuick 2.15
import "../theme"

// Keyboard focus ring around its parent control: shown only when focus came from the keyboard (visualFocus),
// never on mouse clicks. Put one inside a Control.
Rectangle {
    z: 10
    anchors.fill: parent
    anchors.margins: -3
    radius: Theme.radiusSm + 3
    color: "transparent"
    border.width: 2
    border.color: Theme.focusRing
    visible: parent.visualFocus
}
