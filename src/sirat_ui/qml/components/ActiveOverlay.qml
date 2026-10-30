pragma Singleton
import QtQuick 2.15

// The overlay of the window the user is working in, so dialogs open there and not behind a pop-out.
// OverlayTracker keeps it up to date, one per window.
QtObject {
    property Item current: null
    property Item home: null    // the main window's overlay: where dialogs go when a pop-out closes
}
