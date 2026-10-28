import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../theme"
import "../../components"

// Header + rows for register fields. Column widths live here so header and rows always agree.
Item {
    id: table
    property alias model: list.model
    property bool showCalculated: false
    signal valueEdited(int row, string text)
    signal noteEdited(int row, string text)
    signal watchClicked(int row)
    signal loggerClicked(int row)
    signal formulaClicked(int row)

    readonly property var columns: ({
        bits: 50, name: 150, access: 64, value: 84, enumName: 110,
        calc: showCalculated ? 120 : 0, actions: 92, notes: 210
    })
    readonly property real descWidth: Math.max(160, width - 24 - columns.bits - columns.name - columns.access
                                               - columns.value - columns.enumName - columns.calc
                                               - columns.actions - columns.notes)

    Row {
        id: header
        x: 12
        height: 30
        Repeater {
            model: [
                { label: "Bits", w: table.columns.bits }, { label: "Name", w: table.columns.name },
                { label: "Access", w: table.columns.access }, { label: "Value", w: table.columns.value },
                { label: "Enum", w: table.columns.enumName }, { label: "Calculated", w: table.columns.calc },
                { label: "Description", w: table.descWidth }, { label: "", w: table.columns.actions },
                { label: "Notes", w: table.columns.notes }
            ]
            delegate: Text {
                width: modelData.w
                height: header.height
                visible: modelData.w > 0
                text: modelData.label
                verticalAlignment: Text.AlignVCenter
                font.family: Theme.fontUi
                font.pixelSize: Theme.fontXs
                font.weight: Font.DemiBold
                color: Theme.textMuted
                elide: Text.ElideRight
            }
        }
    }

    Rectangle {
        anchors.top: header.bottom
        width: parent.width
        height: 1
        color: Theme.border
    }

    ListView {
        id: list
        anchors.top: header.bottom
        anchors.topMargin: 1
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: AppScrollBar {}
        delegate: FieldRow {
            columns: table.columns
            descWidth: table.descWidth
            onValueEdited: table.valueEdited(index, text)
            onNoteEdited: table.noteEdited(index, text)
            onWatchClicked: table.watchClicked(index)
            onLoggerClicked: table.loggerClicked(index)
            onFormulaClicked: table.formulaClicked(index)
        }
    }
}
