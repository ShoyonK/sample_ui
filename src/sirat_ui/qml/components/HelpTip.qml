import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// A small "?" that explains something. Hover to show; click to keep it open (click again or press Esc to close).
// text accepts simple markup: <b>, <i>, <br>.
Rectangle {
    id: root
    property string text: ""
    property int tipWidth: 380
    property bool pinned: false
    readonly property bool open: tip.visible

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: "Help"
    Accessible.description: text.replace(/<[^>]+>/g, " ")
    Keys.onSpacePressed: root.pinned = !root.pinned
    Keys.onReturnPressed: root.pinned = !root.pinned
    implicitWidth: 18
    implicitHeight: 18
    radius: width / 2
    color: hover.hovered || pinned ? Theme.surface2 : "transparent"
    border.color: activeFocus ? Theme.focusRing : hover.hovered || pinned ? Theme.textMuted : Theme.borderStrong
    border.width: activeFocus ? 2 : 1

    Text {
        anchors.centerIn: parent
        text: "?"
        font.family: Theme.fontUi
        font.pixelSize: Theme.fontXs
        font.weight: Font.Bold
        color: hover.hovered || root.pinned ? Theme.textPrimary : Theme.textMuted
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor; onHoveredChanged: root.sync() }
    TapHandler { onTapped: root.pinned = !root.pinned }
    onPinnedChanged: sync()
    onVisibleChanged: sync()

    // Opened and closed explicitly: a binding on a Popup's visible breaks when the popup closes itself.
    function sync() {
        var want = root.visible && root.text !== "" && (hover.hovered || root.pinned)
        if (!want) {
            hoverDelay.stop()
            tip.close()
        } else if (root.pinned) {
            tip.open()
        } else if (!tip.opened) {
            hoverDelay.restart()
        }
    }

    Timer { id: hoverDelay; interval: 250; onTriggered: if (hover.hovered && !tip.opened) tip.open() }

    ToolTip {
        id: tip
        objectName: root.objectName ? root.objectName + "Popup" : ""
        delay: 0
        x: 0
        y: root.height + 6
        padding: 12
        width: root.tipWidth + leftPadding + rightPadding  // otherwise it sizes to the unwrapped text
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        onClosed: root.pinned = false
        background: Rectangle {
            radius: Theme.radiusSm
            color: Theme.surface
            border.color: Theme.borderStrong
        }
        contentItem: Text {
            width: root.tipWidth
            text: root.text
            textFormat: Text.StyledText
            wrapMode: Text.WordWrap
            lineHeight: 1.25
            font.family: Theme.fontUi
            font.pixelSize: Theme.fontSm
            color: Theme.textPrimary
        }
    }
}
