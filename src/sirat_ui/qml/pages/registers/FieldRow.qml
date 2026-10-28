import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../theme"
import "../../components"

Rectangle {
    id: row
    property var columns
    property real descWidth: 200
    property bool editing: false
    signal valueEdited(string text)
    signal noteEdited(string text)
    signal watchClicked()
    signal loggerClicked()
    signal formulaClicked()

    objectName: "fieldRow_" + model.name
    width: ListView.view ? ListView.view.width : 900
    height: Math.max(40, descText.implicitHeight + 16)
    color: hover.hovered ? Theme.surface2 : "transparent"
    HoverHandler { id: hover }

    Row {
        x: 12
        height: parent.height

        Text {
            width: row.columns.bits; height: parent.height
            text: model.bits
            verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; color: Theme.textPrimary
        }
        Text {
            width: row.columns.name; height: parent.height
            text: model.name
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary
        }
        Item {
            width: row.columns.access; height: parent.height
            Chip { anchors.verticalCenter: parent.verticalCenter; text: model.accessText; tone: Theme.accessTone(model.accessKey) }
        }

        // value: double-click to edit when writable, Enter writes (req 5 auto-write)
        Rectangle {
            width: row.columns.value - 8; height: parent.height
            color: model.changed ? Theme.changed : "transparent"
            Text {
                visible: !row.editing
                anchors.fill: parent
                anchors.leftMargin: 6
                text: model.valueText
                verticalAlignment: Text.AlignVCenter
                font.family: Theme.fontMono; font.pixelSize: Theme.fontSm
                color: model.hasValue ? (model.editable ? Theme.textPrimary : Theme.textMuted) : Theme.borderStrong
            }
            AppTextField {
                id: valueEditor
                objectName: "fieldValueEditor_" + model.name
                visible: row.editing
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                mono: true
                onAccepted: { row.editing = false; row.valueEdited(text) }
                onActiveFocusChanged: if (!activeFocus) row.editing = false
                Keys.onEscapePressed: row.editing = false
            }
            TapHandler {
                enabled: model.editable && !row.editing
                onDoubleTapped: {
                    valueEditor.text = model.valueText === "—" ? "" : model.valueText
                    row.editing = true
                    valueEditor.forceActiveFocus()
                    valueEditor.selectAll()
                }
            }
            // req 5 tooltips: changed value, or a value not read yet
            ToolTip.visible: valueHover.hovered && (model.changedTip !== "" || !model.hasValue)
            ToolTip.text: model.changedTip !== "" ? model.changedTip : "Value not read yet - may not be accurate"
            HoverHandler { id: valueHover }
        }
        Item { width: 8; height: 1 }

        Text {
            width: row.columns.enumName; height: parent.height
            text: model.enumName || "—"
            verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm
            color: model.enumName ? Theme.okFg : Theme.borderStrong
        }
        Text {
            visible: row.columns.calc > 0
            width: row.columns.calc; height: parent.height
            text: model.calcText || "—"
            verticalAlignment: Text.AlignVCenter
            font.family: Theme.fontMono; font.pixelSize: Theme.fontSm
            color: model.calcText ? Theme.infoFg : Theme.borderStrong
            HoverHandler { id: calcHover }
            ToolTip.visible: calcHover.hovered && model.calcText !== ""
            ToolTip.text: "Calculated value from formula"
        }
        Text {
            id: descText
            width: row.descWidth; height: parent.height
            text: model.description
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            rightPadding: 8
            font.family: Theme.fontUi; font.pixelSize: Theme.fontMd; color: Theme.textMuted
        }
        Row {
            width: row.columns.actions; height: parent.height
            spacing: 2
            IconButton {
                anchors.verticalCenter: parent.verticalCenter
                objectName: "watchButton_" + model.name
                iconName: "eye"; tip: "Add to watch list"
                onClicked: row.watchClicked()
            }
            IconButton {
                anchors.verticalCenter: parent.verticalCenter
                objectName: "loggerButton_" + model.name
                iconName: "chart"; tip: "Add to data logger"
                onClicked: row.loggerClicked()
            }
            IconButton {
                anchors.verticalCenter: parent.verticalCenter
                objectName: "formulaButton_" + model.name
                iconName: "edit"; tip: model.hasFormula ? "Edit formula" : "Add formula"
                iconColor: model.hasFormula ? Theme.infoFg : Theme.textMuted
                onClicked: row.formulaClicked()
            }
        }

        // notes: always editable, auto-saved (req 10)
        Rectangle {
            width: row.columns.notes; height: parent.height
            color: model.hasNote ? Theme.noteBg : "transparent"
            HoverHandler { id: noteHover }
            ToolTip.visible: noteHover.hovered && !noteInput.activeFocus
            ToolTip.text: "Click to edit note"
            ToolTip.delay: 600
            TextInput {
                id: noteInput
                objectName: "noteInput_" + model.name
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                verticalAlignment: TextInput.AlignVCenter
                text: model.note
                clip: true
                selectByMouse: true
                font.family: Theme.fontUi; font.pixelSize: Theme.fontMd; color: Theme.textPrimary
                onEditingFinished: row.noteEdited(text)
                Text {
                    visible: !noteInput.text && !noteInput.activeFocus
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Add a note"
                    font: noteInput.font
                    color: Theme.textMuted
                }
            }
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
