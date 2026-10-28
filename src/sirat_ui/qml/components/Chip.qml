import QtQuick 2.15
import "../theme"

// tones: info, ok, warn, danger, split, mute. Or set accent to any color (e.g. Theme.kindColor).
Rectangle {
    id: root
    property string text: ""
    property string tone: "mute"
    property bool mono: false
    property color accent: "transparent"
    readonly property bool hasAccent: accent.a > 0

    implicitWidth: label.implicitWidth + 14
    implicitHeight: 20
    radius: 5
    color: hasAccent ? Qt.rgba(accent.r, accent.g, accent.b, Theme.dark ? 0.22 : 0.12) : Theme.toneBg(tone)

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.hasAccent ? root.accent : Theme.toneFg(root.tone)
        font.family: root.mono ? Theme.fontMono : Theme.fontUi
        font.pixelSize: Theme.fontXs
        font.weight: Font.DemiBold
    }
}
