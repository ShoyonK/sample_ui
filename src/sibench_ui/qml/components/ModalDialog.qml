import QtQuick 2.15
import QtQml 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import "../theme"

// Centered modal card. Content goes in contentItem; closes only through the caller's buttons.
// Bind `shown` to the ViewModel's open state, not `visible`: Qt ignores open() while the closing animation runs,
// so a dialog reopened in that moment would stay closed while its ViewModel thinks it's open.
Popup {
    id: popup
    property int dialogWidth: 480
    property bool shown: false

    onShownChanged: shown ? open() : close()
    onClosed: if (shown) Qt.callLater(popup.reopen)   // after it has moved to the window in use
    function reopen() { if (shown && !visible) open() }
    Component.onCompleted: if (shown) open()

    // Opens in the window in use, and stays there while it's open even if another window gets clicked. A pop-out
    // that closes hands its dialogs back (OverlayTracker), so they move once closed and can always open again.
    Binding on parent {
        when: !popup.visible
        value: ActiveOverlay.current || popup.Overlay.overlay
        restoreMode: Binding.RestoreNone
    }
    // Open in a pop-out that closes: move to the window in use now, or it would be modal but out of sight
    Connections {
        target: ActiveOverlay
        function onCurrentChanged() {
            var item = popup.parent
            var win = item ? item.Window.window : null
            if (popup.visible && ActiveOverlay.current && (!win || !win.visible))
                popup.parent = ActiveOverlay.current
        }
    }
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
