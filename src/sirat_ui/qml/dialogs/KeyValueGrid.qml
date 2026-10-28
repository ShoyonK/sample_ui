import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    property var rows: []   // [{ key, value }]
    property bool monoValues: true

    implicitHeight: grid.implicitHeight + 24
    radius: Theme.radius
    color: Theme.surface2
    border.color: Theme.border
    visible: rows.length > 0

    GridLayout {
        id: grid
        anchors.fill: parent
        anchors.margins: 12
        columns: 2
        columnSpacing: 12
        rowSpacing: 6
        Repeater {
            model: rows.length * 2
            delegate: Text {
                readonly property var entry: rows[Math.floor(index / 2)]
                readonly property bool isKey: index % 2 === 0
                text: isKey ? entry.key : entry.value
                font.family: isKey || !monoValues ? Theme.fontUi : Theme.fontMono
                font.pixelSize: Theme.fontSm
                font.weight: !isKey && entry.key === "New value" ? Font.Bold : Font.Normal
                color: isKey ? Theme.textMuted : Theme.textPrimary
                Layout.preferredWidth: isKey ? 110 : -1
                Layout.fillWidth: !isKey
            }
        }
    }
}
