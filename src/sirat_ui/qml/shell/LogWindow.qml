import QtQuick 2.15
import QtQuick.Window 2.15
import "../theme"
import "../pages/dock"

// Req 35 pop-out: the log in its own window, synced with the dock panel.
Window {
    id: logWindow
    objectName: "logWindow"
    title: "SiRAT — Log"
    width: 900
    height: 600
    color: Theme.canvas
    visible: app.log.poppedOut
    onClosing: app.log.setPoppedOut(false)

    LogPanel {
        anchors.fill: parent
        anchors.margins: 10
        inWindow: true
    }
}
