import QtQuick 2.15
import "../theme"

// White surface with a hairline border. Children lay themselves out inside.
Rectangle {
    color: Theme.surface
    radius: Theme.radius
    border.color: Theme.border
    border.width: 1
    clip: true
}
