import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

// Put one in every window: tells ActiveOverlay when this window becomes the one in use.
Item {
    property bool isHome: false
    readonly property bool windowActive: Window.active
    readonly property bool windowShown: Window.visibility !== Window.Hidden
    readonly property Item overlay: Overlay.overlay

    function handBack() { if (ActiveOverlay.current === overlay) ActiveOverlay.current = ActiveOverlay.home }

    onWindowActiveChanged: if (windowActive) ActiveOverlay.current = overlay
    // A pop-out closing hides at once but is destroyed later: hand dialogs back as soon as it hides
    onWindowShownChanged: if (!windowShown && !isHome) handBack()
    Component.onCompleted: {
        if (isHome)
            ActiveOverlay.home = overlay
        if (windowActive || isHome)
            ActiveOverlay.current = overlay
    }
    Component.onDestruction: handBack()
}
