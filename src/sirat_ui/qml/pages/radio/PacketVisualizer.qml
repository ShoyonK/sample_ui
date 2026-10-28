import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"

// Req 23 live packet visualizer: the PPDU's fields left to right. Legacy preamble in blue, the standard's own
// fields in purple, data in green; the data block takes the remaining width.
Rectangle {
    id: root
    property var segments: []
    property string caption: ""

    implicitHeight: 150
    radius: Theme.radius
    color: Theme.surface2
    border.color: Theme.border

    function bg(kind) { return kind === "legacy" ? Theme.infoBg : kind === "standard" ? Theme.splitBg
                             : kind === "data" ? Theme.okBg : Theme.select }
    function fg(kind) { return kind === "legacy" ? Theme.infoFg : kind === "standard" ? Theme.splitFg
                             : kind === "data" ? Theme.okFg : Theme.textMuted }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.s3
        spacing: Theme.s2
        Text { text: "Packet structure"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 3
            Repeater {
                model: root.segments
                delegate: Rectangle {
                    objectName: "segment_" + modelData.name
                    Layout.fillHeight: true
                    Layout.fillWidth: modelData.kind === "data"
                    Layout.preferredWidth: modelData.kind === "data" ? 160 : Math.max(name.implicitWidth + 14, 52)
                    radius: Theme.radiusSm
                    color: root.bg(modelData.kind)
                    Column {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            id: name
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.name
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontXs
                            font.weight: Font.DemiBold
                            color: root.fg(modelData.kind)
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.label
                            visible: text !== ""
                            font.pixelSize: Theme.fontXs
                            color: root.fg(modelData.kind)
                        }
                    }
                }
            }
        }
        Text {
            objectName: "packetCaption"
            text: root.caption
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }
}
