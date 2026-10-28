import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// Dark run-output console with colored levels and a Clear button (req 13 large view, req 14).
Rectangle {
    id: panel
    property var model
    property string title: "Console"
    signal clearRequested()

    radius: Theme.radius
    color: Theme.consoleBg

    Text {
        id: heading
        x: 12
        y: 8
        text: panel.title
        font.pixelSize: Theme.fontXs
        font.weight: Font.DemiBold
        color: "#9A9A9A"
    }
    AbstractButton {
        objectName: "consoleClear_" + panel.title
        anchors.right: parent.right
        anchors.rightMargin: 8
        y: 4
        width: clearLabel.implicitWidth + 16
        height: 20
        hoverEnabled: true
        onClicked: panel.clearRequested()
        background: Rectangle { radius: 4; color: parent.hovered ? "#2A2A2A" : "transparent" }
        contentItem: Text {
            id: clearLabel
            text: "Clear"
            font.pixelSize: Theme.fontXs
            color: "#BDBDBD"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    ListView {
        id: lines
        anchors.fill: parent
        anchors.topMargin: 28
        anchors.margins: 12
        clip: true
        model: panel.model
        onCountChanged: positionViewAtEnd()
        ScrollBar.vertical: AppScrollBar {}
        delegate: Text {
            width: ListView.view ? ListView.view.width : 400
            text: "<font color='#7A7A7A'>" + model.time + "</font>  " + model.text.replace(/&/g, "&amp;").replace(/</g, "&lt;")
            textFormat: Text.StyledText
            wrapMode: Text.WrapAnywhere
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: model.level === "success" ? "#7EE29A" : model.level === "error" ? "#FF8A8A"
                 : model.level === "warning" ? "#FFC66B" : "#8EC7FF"
        }
    }
}
