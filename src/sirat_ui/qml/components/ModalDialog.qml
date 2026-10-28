import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// Centered modal card. Content goes in contentItem; closes only through the caller's buttons.
Popup {
    id: popup
    property int dialogWidth: 480

    parent: Overlay.overlay
    modal: true
    dim: true
    focus: true
    closePolicy: Popup.NoAutoClose
    width: dialogWidth
    // Qt 5 layouts keep a stale implicit height after word-wrapped text first measures at zero width,
    // so measure where the children actually ended up once layout settles (+ the content's bottom margin).
    // callLater instead of a binding avoids a height <-> childrenRect binding loop.
    property int contentBottomMargin: 36  // the content's own 18px bottom margin, plus breathing room
    property real fittedHeight: implicitHeight
    height: fittedHeight

    function refit() {
        if (contentItem && contentItem.childrenRect.height > 0)
            fittedHeight = contentItem.childrenRect.height + contentBottomMargin
    }
    onOpened: Qt.callLater(refit)
    Connections {
        target: popup.contentItem
        function onChildrenRectChanged() { Qt.callLater(popup.refit) }
    }
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    padding: 0

    background: Rectangle {
        radius: 12
        color: Theme.surface
        border.color: Theme.border
    }
    Overlay.modal: Rectangle { color: Theme.overlay }

    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 90 } }
}
