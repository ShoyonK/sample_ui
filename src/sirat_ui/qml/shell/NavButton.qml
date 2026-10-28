import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
import "../components"

// A nav rail tab. Right-click: open the page in its own window, show that window, or bring it back.
AbstractButton {
    id: control
    property string pageKey: ""
    property string iconName: "cpu"
    property string tip: ""
    property bool current: false
    property bool ready: true
    property bool poppedOut: false
    signal popOutRequested()
    signal showWindowRequested()
    signal dockRequested()

    objectName: "nav_" + pageKey
    implicitWidth: 40
    implicitHeight: 40
    hoverEnabled: true

    contentItem: Icon {
        name: control.iconName
        size: 18
        color: control.current || control.hovered ? Theme.textPrimary : Theme.textMuted
        opacity: control.ready ? 1 : 0.55
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.current || control.hovered ? Theme.select : "transparent"
    }

    // Badge: this page is in its own window
    Rectangle {
        objectName: "navPopped_" + control.pageKey
        visible: control.poppedOut
        width: 14
        height: 14
        radius: 7
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: -2
        color: Theme.infoBg
        border.color: Theme.surface
        Icon { anchors.centerIn: parent; name: "export"; size: 8; color: Theme.infoFg }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: menu.popup()
    }

    AppMenu {
        id: menu
        objectName: "navMenu_" + control.pageKey
        AppMenuItem {
            objectName: "navMenuPopOut_" + control.pageKey
            text: "Open in new window"
            iconName: "export"
            visible: !control.poppedOut
            onTriggered: control.popOutRequested()
        }
        AppMenuItem {
            objectName: "navMenuShow_" + control.pageKey
            text: "Show its window"
            iconName: "export"
            visible: control.poppedOut
            onTriggered: control.showWindowRequested()
        }
        AppMenuItem {
            objectName: "navMenuDock_" + control.pageKey
            text: "Bring back to main window"
            iconName: "download"
            visible: control.poppedOut
            onTriggered: control.dockRequested()
        }
    }

    ToolTip.visible: hovered && tip !== "" && !menu.visible
    ToolTip.text: tip + (poppedOut ? " (in its own window)" : "") + "\nRight-click to open in a new window"
    ToolTip.delay: 300
}
