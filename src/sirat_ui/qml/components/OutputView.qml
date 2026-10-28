import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// Dark Python output for the Advanced tools (req 15, 20, 22): echoed input, stdout, results, errors, hints
// and notes, each block selectable. Copy takes everything; Clear empties it.
Rectangle {
    id: panel
    property var model
    property string title: "Output"
    property string prefix: "output"
    property string emptyText: ""

    radius: Theme.radius
    color: Theme.consoleBg

    readonly property var colors: ({
        input: "#E8D37A", stdout: Theme.consoleText, result: "#7EE29A", error: "#FF8A8A",
        hint: "#FFC66B", note: "#8A8A8A"
    })

    Text {
        x: 12
        y: 8
        text: panel.title
        font.pixelSize: Theme.fontXs
        font.weight: Font.DemiBold
        color: "#9A9A9A"
    }
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 8
        y: 4
        spacing: 2
        Repeater {
            model: [{ key: "Copy", tip: "Copy all output" }, { key: "Clear", tip: "Clear the output" }]
            delegate: AbstractButton {
                objectName: panel.prefix + modelData.key + "Button"
                width: label.implicitWidth + 16
                height: 20
                hoverEnabled: true
                enabled: lines.count > 0
                opacity: enabled ? 1 : 0.4
                Accessible.name: modelData.tip
                onClicked: modelData.key === "Copy" ? panel.model.copyAll() : panel.model.clear()
                background: Rectangle { radius: 4; color: parent.hovered ? "#2A2A2A" : "transparent" }
                contentItem: Text {
                    id: label
                    text: modelData.key
                    font.pixelSize: Theme.fontXs
                    color: "#BDBDBD"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
    ListView {
        id: lines
        objectName: panel.prefix + "Lines"
        anchors.fill: parent
        anchors.topMargin: 30
        anchors.leftMargin: 12
        anchors.rightMargin: 6
        anchors.bottomMargin: 8
        clip: true
        spacing: 2
        model: panel.model
        boundsBehavior: Flickable.StopAtBounds
        onCountChanged: positionViewAtEnd()
        ScrollBar.vertical: AppScrollBar {}
        delegate: TextEdit {
            width: ListView.view ? ListView.view.width - 10 : 400
            text: model.text
            readOnly: true
            selectByMouse: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.WrapAnywhere
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            font.italic: model.level === "note"
            color: panel.colors[model.level] || Theme.consoleText
            selectionColor: "#3B5BDB"
            selectedTextColor: "#FFFFFF"
        }
    }
    Text {
        visible: lines.count === 0 && panel.emptyText !== ""
        anchors.centerIn: parent
        width: parent.width - 48
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        text: panel.emptyText
        font.pixelSize: Theme.fontSm
        color: "#7A7A7A"
    }
}
