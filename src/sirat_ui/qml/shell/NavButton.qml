import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
import "../components"

// A nav rail tab. Right-click: open the page in its own window, show that window, or bring it back; then the
// same for each of the page's parts (domains/shell/tools.py), such as the data logger on Watch.
AbstractButton {
    id: control
    property string pageKey: ""
    property string iconName: "cpu"
    property string label: ""
    property string tip: ""
    property bool current: false
    property bool ready: true
    property bool poppedOut: false
    property var parts: []          // {kind, arg, key, title}
    property var openKeys: []       // app.windows.openKeys
    signal popOutRequested()
    signal showWindowRequested()
    signal dockRequested()
    signal partPopOutRequested(string kind, string arg)
    signal partDockRequested(string key)

    function partOpen(key) { return control.openKeys.indexOf(key) >= 0 }

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
            text: "Open page in new window"
            iconName: "export"
            visible: !control.poppedOut
            onTriggered: control.popOutRequested()
        }
        AppMenuItem {
            objectName: "navMenuShow_" + control.pageKey
            text: "Show page window"
            iconName: "export"
            visible: control.poppedOut
            onTriggered: control.showWindowRequested()
        }
        AppMenuItem {
            objectName: "navMenuDock_" + control.pageKey
            text: "Bring page back"
            iconName: "download"
            visible: control.poppedOut
            onTriggered: control.dockRequested()
        }
        MenuSeparator {
            visible: control.parts.length > 0
            height: visible ? implicitHeight : 0
            contentItem: Rectangle { implicitHeight: 1; color: Theme.border }
        }
        Instantiator {
            model: control.parts
            delegate: AppMenuItem {
                objectName: "navMenuPart_" + modelData.key
                text: control.partOpen(modelData.key) ? "Bring back " + modelData.title
                                                      : "Open " + modelData.title + " in new window"
                iconName: control.partOpen(modelData.key) ? "download" : "export"
                onTriggered: control.partOpen(modelData.key) ? control.partDockRequested(modelData.key)
                                                             : control.partPopOutRequested(modelData.kind, modelData.arg)
            }
            onObjectAdded: menu.insertItem(menu.count, object)
            onObjectRemoved: menu.removeItem(object)
        }
    }

    ToolTip.visible: hovered && tip !== "" && !menu.visible
    ToolTip.text: tip + (poppedOut ? " (in its own window)" : "") + "\nRight-click to open in a new window"
    ToolTip.delay: 300
}
