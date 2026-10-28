import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"

// 32 toggle cells in four byte groups [31..24] [23..16] [15..8] [7..0] (req 5).
RowLayout {
    id: grid
    property var bitValues: []
    property var fieldBits: []
    property bool interactive: true
    signal bitClicked(int bit)

    spacing: 16

    function byteHex(byteIndex) {
        var v = 0
        for (var i = 0; i < 8; i++)
            if (bitValues[byteIndex * 8 + i]) v |= (1 << i)
        return "0x" + ("0" + v.toString(16).toUpperCase()).slice(-2)
    }

    Repeater {
        model: 4
        delegate: Column {
            readonly property int byteIndex: 3 - index
            // equal preferred widths make the four byte groups share the row evenly
            Layout.fillWidth: true
            Layout.preferredWidth: 100
            spacing: 4

            RowLayout {
                width: parent.width
                Text { text: "Byte " + byteIndex; font.pixelSize: Theme.fontXs; color: Theme.textMuted; Layout.fillWidth: true }
                Text { text: grid.byteHex(byteIndex); font.family: Theme.fontMono; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
            }

            Row {
                spacing: 4
                width: parent.width
                Repeater {
                    model: 8
                    delegate: Rectangle {
                        id: cell
                        readonly property int bit: byteIndex * 8 + (7 - index)
                        readonly property bool on: !!grid.bitValues[bit]
                        objectName: "bit_" + bit
                        width: (parent.width - 28) / 8
                        height: 30
                        radius: 5
                        readonly property bool hot: cellHover.hovered && grid.interactive
                        color: on ? Theme.bitOn : (hot ? Theme.bitHover : Theme.surface2)
                        border.color: on || hot ? Theme.bitOnBorder : Theme.borderStrong
                        scale: tap.pressed ? 0.92 : (hot ? 1.06 : 1.0)

                        Behavior on color { ColorAnimation { duration: 140 } }
                        Behavior on border.color { ColorAnimation { duration: 140 } }
                        Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

                        // a quick pulse whenever the bit flips, including flips from reads and watch updates
                        onOnChanged: pulse.restart()
                        SequentialAnimation {
                            id: pulse
                            NumberAnimation { target: cell; property: "scale"; to: 1.15; duration: 90; easing.type: Easing.OutQuad }
                            NumberAnimation { target: cell; property: "scale"; to: 1.0; duration: 160; easing.type: Easing.OutBack }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: cell.on ? "1" : "0"
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSm
                            font.weight: Font.DemiBold
                            color: cell.on || cell.hot ? Theme.bitOnText : Theme.textMuted
                        }
                        Rectangle {
                            visible: !!grid.fieldBits[cell.bit]
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: 3
                            height: 2
                            radius: 1
                            color: Theme.bitOnText
                            opacity: cell.on ? 0.7 : 0.45
                        }
                        HoverHandler {
                            id: cellHover
                            cursorShape: grid.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
                        }
                        TapHandler {
                            id: tap
                            enabled: grid.interactive
                            onTapped: grid.bitClicked(cell.bit)
                        }
                    }
                }
            }

            Row {
                spacing: 4
                width: parent.width
                Repeater {
                    model: 8
                    delegate: Text {
                        width: (parent.width - 28) / 8
                        horizontalAlignment: Text.AlignHCenter
                        text: byteIndex * 8 + (7 - index)
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontTiny
                        color: Theme.textMuted
                    }
                }
            }
        }
    }
}
