import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// The console's input (req 20): Enter submits, Shift+Enter adds a line, ↑ on the first line and ↓ on the
// last line step through history. `value` is the ViewModel's draft; typing emits edited(text).
Rectangle {
    id: root
    property string value: ""
    property bool busy: false
    property alias field: area
    signal edited(string text)
    signal submitted()
    signal historyPrevious()
    signal historyNext()

    implicitHeight: Math.min(160, Math.max(36, area.implicitHeight + 2))
    radius: Theme.radiusSm
    color: Theme.surface
    border.color: area.activeFocus ? Theme.textPrimary : Theme.borderStrong

    onValueChanged: if (area.text !== value) { area.text = value; area.cursorPosition = area.length }

    Text {
        id: prompt
        x: 10
        y: area.topPadding + 1
        text: root.busy ? "…" : ">>>"
        font.family: Theme.fontMono
        font.pixelSize: Theme.fontMd
        color: Theme.infoFg
    }
    ScrollView {
        anchors.fill: parent
        anchors.leftMargin: prompt.x + prompt.implicitWidth + 4
        clip: true
        TextArea {
            id: area
            objectName: "consoleInputArea"
            padding: 8
            wrapMode: TextEdit.WrapAnywhere
            selectByMouse: true
            textFormat: TextEdit.PlainText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontMd
            color: Theme.textPrimary
            selectionColor: Theme.infoFg
            selectedTextColor: "#FFFFFF"
            placeholderText: "Python code · Enter runs, Shift+Enter adds a line, ↑ / ↓ history"
            placeholderTextColor: Theme.textMuted
            background: null
            Accessible.name: "Python command"
            onTextChanged: if (text !== root.value) root.edited(text)
            Keys.onPressed: function(event) {
                var enter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                if (enter && !(event.modifiers & Qt.ShiftModifier)) {
                    root.submitted()
                    event.accepted = true
                } else if (event.key === Qt.Key_Up && text.lastIndexOf("\n", cursorPosition - 1) < 0) {
                    root.historyPrevious()
                    event.accepted = true
                } else if (event.key === Qt.Key_Down && text.indexOf("\n", cursorPosition) < 0) {
                    root.historyNext()
                    event.accepted = true
                }
            }
        }
    }
}
