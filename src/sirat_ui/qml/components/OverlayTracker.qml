import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

// Put one in every window: tells ActiveOverlay when this window becomes the one in use.
Item {
    property bool isHome: false
    readonly property bool windowActive: Window.active
    readonly property Item overlay: Overlay.overlay

    onWindowActiveChanged: if (windowActive) ActiveOverlay.current = overlay
    Component.onCompleted: {
        if (isHome)
            ActiveOverlay.home = overlay
        if (windowActive || isHome)
            ActiveOverlay.current = overlay
    }
    Component.onDestruction: if (ActiveOverlay.current === overlay) ActiveOverlay.current = ActiveOverlay.home
}
