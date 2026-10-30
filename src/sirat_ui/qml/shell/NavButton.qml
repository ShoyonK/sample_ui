import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
import "../components"

// A nav rail tab. Right-click: open the page in its own window, show that window, or bring it back.
AbstractButton {
    id: control
    property string pageKey: ""
    property string iconName: "cpu"
    property string label: ""
    property string tip: ""
    property bool current: false
    property bool ready: true
    property bool poppedOut: false
    signal popOutRequested()
    signal showWindowRequested()
    signal dockRequested()

    objectName: "nav_" + pageKey
    implicitWidth: 60
    implicitHeight: 48
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.PageTab
    Accessible.name: label
    Accessible.description: tip

    // icon over a short label, so pages are recognized without hovering
    contentItem: Item {
        opacity: control.ready ? 1 : 0.55
        Column {
            anchors.centerIn: parent
            spacing: 3
            Icon {
                anchors.horizontalCenter: parent.horizontalCenter
                name: control.iconName
                size: 18
                color: control.current || control.hovered ? Theme.textPrimary : Theme.textMuted
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: control.label
                font.family: Theme.fontUi
                font.pixelSize: Theme.fontXs
                font.weight: control.current ? Font.DemiBold : Font.Normal
                color: control.current || control.hovered ? Theme.textPrimary : Theme.textMuted
            }
        }
    }
    background: Rectangle {
        radius: Theme.radius
        color: control.current || control.hovered ? Theme.select : "transparent"
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.focusRing
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

    // A MouseArea, not a TapHandler: with a TapHandler the button still sees the right-click and fires clicked.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: menu.popup(mouse.x, mouse.y)
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
