import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One finished test: name, Pass or Fail, notes, start time and duration (req 33 results table).
Rectangle {
    id: row
    property var columns   // the page's results column table, shared with its header
    signal activated()

    objectName: "testResult_" + model.id
    width: ListView.view ? ListView.view.width : 900
    height: 40
    color: Theme.rowColor(model.selected, hover.hovered)
    HoverHandler { id: hover }
    TapHandler { onTapped: row.activated() }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 10

        Text {
            text: model.num
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            Layout.preferredWidth: row.columns.num
        }
        Text {
            text: model.name
            font.pixelSize: Theme.fontMd
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.preferredWidth: row.columns.name
        }
        Chip {
            objectName: "testStatus_" + model.id
            text: model.status
            tone: model.status === "Pass" ? "ok" : "danger"
            Layout.preferredWidth: row.columns.status
        }
        Text {
            text: model.notes
            font.pixelSize: Theme.fontSm
            color: model.status === "Pass" ? Theme.textMuted : Theme.dangerFg
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: model.startedText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            Layout.preferredWidth: row.columns.started
        }
        Text {
            text: model.durationText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: Theme.textMuted
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: row.columns.duration
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.border
    }
}
