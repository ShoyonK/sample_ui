import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"

// One hex dump line: address (click to use it as the write address), cells, ASCII. Cells that changed
// since the previous read of the same block are highlighted.
Item {
    id: row
    signal addressClicked()
    readonly property var cells: model.cells    // copied out: the Repeater's own `model` would shadow it
    readonly property bool bytes: cells.length > 0 && cells[0].t.length === 2

    width: ListView.view ? ListView.view.width : 900
    height: 20

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        spacing: 0
        Text {
            text: model.address
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            font.underline: tap.hovered
            color: Theme.textMuted
            Layout.preferredWidth: 104
            HoverHandler { id: tap; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: row.addressClicked() }
        }
        Repeater {
            model: row.cells
            delegate: Rectangle {
                implicitWidth: cell.implicitWidth + (row.bytes ? 8 : 12) + (row.bytes && index === 8 ? 10 : 0)
                implicitHeight: 18
                color: "transparent"
                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: row.bytes ? 2 : 4
                    anchors.verticalCenter: parent.verticalCenter
                    width: cell.implicitWidth + 4
                    height: 16
                    radius: 3
                    color: modelData.c ? Theme.changed : "transparent"
                }
                Text {
                    id: cell
                    anchors.right: parent.right
                    anchors.rightMargin: row.bytes ? 4 : 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.t
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSm
                    color: Theme.textPrimary
                }
            }
        }
        Text {
            visible: model.ascii !== ""
            text: model.ascii
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            Layout.leftMargin: 18
        }
        Item { Layout.fillWidth: true }
    }
}
