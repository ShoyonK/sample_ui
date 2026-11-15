import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// Dark run-output console with colored levels and a Clear button (req 13 large view, req 14).
Rectangle {
    id: panel
    property var model
    property string title: "Console"
    property bool clearable: true
    signal clearRequested()

    radius: Theme.radius
    color: Theme.consoleBg

    readonly property var levelColors: ({ success: Theme.consoleOk, error: Theme.consoleError,
                                          warning: Theme.consoleWarn })

    Text {
        id: heading
        x: 12
        y: 8
        text: panel.title
        font.pixelSize: Theme.fontXs
        font.weight: Font.DemiBold
        color: Theme.consoleTitle
    }
    AbstractButton {
        objectName: "consoleClear_" + panel.title
        visible: panel.clearable
        anchors.right: parent.right
        anchors.rightMargin: Theme.s2
        y: 4
        width: clearLabel.implicitWidth + 16
        height: 20
        hoverEnabled: true
        Accessible.name: "Clear " + panel.title
        onClicked: panel.clearRequested()
        background: Rectangle { radius: 4; color: parent.hovered ? Theme.consoleHover : "transparent" }
        contentItem: Text {
            id: clearLabel
            text: "Clear"
            font.pixelSize: Theme.fontXs
            color: Theme.consoleButton
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    ListView {
        id: lines
        anchors.fill: parent
        anchors.topMargin: 28
        anchors.margins: Theme.s3
        clip: true
        model: panel.model
        onCountChanged: positionViewAtEnd()
        ScrollBar.vertical: AppScrollBar {}
        delegate: Text {
            width: ListView.view ? ListView.view.width : 400
            text: "<font color='" + Theme.consoleTime + "'>" + model.time + "</font>  "
                  + model.text.replace(/&/g, "&amp;").replace(/</g, "&lt;")
            textFormat: Text.StyledText
            wrapMode: Text.WrapAnywhere
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: panel.levelColors[model.level] || Theme.consoleInfo
        }
    }
}
