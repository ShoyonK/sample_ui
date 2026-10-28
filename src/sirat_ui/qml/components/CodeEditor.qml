import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// A monospace Python editor with line numbers (tracebacks name lines). `code` is the ViewModel's text;
// typing emits edited(text). Tab inserts four spaces; Ctrl+Enter emits runRequested().
// documentReady(doc) hands the QQuickTextDocument to whoever attaches syntax highlighting.
Rectangle {
    id: root
    property string code: ""
    property string placeholder: ""
    property alias editor: area
    signal edited(string text)
    signal runRequested()
    signal documentReady(var doc)

    radius: Theme.radius
    color: Theme.surface
    border.color: area.activeFocus ? Theme.textPrimary : Theme.borderStrong
    clip: true

    onCodeChanged: if (area.text !== code) area.text = code
    Component.onCompleted: {
        area.text = code
        documentReady(area.textDocument)
    }

    Flickable {
        id: flick
        anchors.fill: parent
        anchors.margins: 1
        clip: true
        contentWidth: Math.max(width, gutter.width + area.implicitWidth)
        contentHeight: Math.max(height, area.implicitHeight)
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: AppScrollBar {}
        ScrollBar.horizontal: AppScrollBar {}

        function follow(r) {
            if (r.y < contentY) contentY = r.y
            else if (r.y + r.height > contentY + height) contentY = r.y + r.height - height
            var x = r.x + gutter.width
            if (x < contentX + gutter.width) contentX = Math.max(0, x - gutter.width - 20)
            else if (x > contentX + width - 20) contentX = x - width + 20
        }

        Rectangle {
            id: gutter
            width: Math.max(36, digits.implicitWidth + 18)
            height: flick.contentHeight
            color: Theme.surface2
            Column {
                y: area.topPadding
                width: parent.width
                Repeater {
                    model: Math.max(1, area.lineCount)
                    Text {
                        width: gutter.width - 8
                        height: area.lineCount > 0 ? area.contentHeight / area.lineCount : 16
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                        text: index + 1
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                }
            }
            Text { id: digits; visible: false; text: area.lineCount; font.family: Theme.fontMono; font.pixelSize: Theme.fontXs }
        }

        TextArea {
            id: area
            objectName: "codeEditorArea"
            x: gutter.width
            width: Math.max(flick.width - gutter.width, implicitWidth)
            height: Math.max(flick.height, implicitHeight)
            padding: 10
            wrapMode: TextEdit.NoWrap
            selectByMouse: true
            persistentSelection: true
            textFormat: TextEdit.PlainText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontMd
            color: Theme.textPrimary
            selectionColor: Theme.infoFg
            selectedTextColor: "#FFFFFF"
            placeholderText: root.placeholder
            placeholderTextColor: Theme.textMuted
            background: null
            Accessible.name: "Function code"
            onTextChanged: if (text !== root.code) root.edited(text)
            onCursorRectangleChanged: flick.follow(cursorRectangle)
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Tab) {
                    area.remove(area.selectionStart, area.selectionEnd)
                    area.insert(area.cursorPosition, "    ")
                    event.accepted = true
                } else if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                           && (event.modifiers & Qt.ControlModifier)) {
                    root.runRequested()
                    event.accepted = true
                }
            }
        }
    }
}
