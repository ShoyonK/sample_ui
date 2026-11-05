import QtQuick 2.15
import "../components"

// Where a page shows one of its tools (domains/shell/tools.py): the tool itself, or a placeholder while the
// tool is open in its own window (right-click the page in the nav rail).
Item {
    id: slot
    property string toolKey: ""
    readonly property string windowKey: "tool:" + toolKey
    readonly property bool popped: app.windows.openKeys.indexOf(windowKey) >= 0

    implicitWidth: popped ? placeholder.implicitWidth : (loader.item ? loader.item.implicitWidth : 0)
    implicitHeight: popped ? placeholder.implicitHeight : (loader.item ? loader.item.implicitHeight : 0)

    Loader {
        id: loader
        objectName: "toolSlot_" + slot.toolKey
        anchors.fill: parent
        active: !slot.popped
        source: Qt.resolvedUrl(app.toolSource(slot.toolKey))
    }
    PoppedOutPlaceholder {
        objectName: "toolPlaceholder_" + slot.toolKey
        id: placeholder
        anchors.fill: parent
        visible: slot.popped
        title: app.toolTitle(slot.toolKey)
        onShowRequested: app.windows.show(slot.windowKey)
        onDockRequested: app.windows.close(slot.windowKey)
    }
}
