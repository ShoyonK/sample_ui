import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../theme"
import "../../components"

Rectangle {
    id: row
    signal activated()
    signal removeRequested()

    objectName: "favorite_" + model.fullName
    width: ListView.view ? ListView.view.width : 180
    height: 42
    radius: Theme.radiusSm
    color: hover.hovered ? Theme.surface2 : "transparent"

    HoverHandler { id: hover }
    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: row.activated()
    }
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: menu.popup()
    }
    Menu {
        id: menu
        MenuItem {
            text: "Remove from favorites"
            onTriggered: row.removeRequested()
        }
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        Icon {
            name: "starFilled"
            size: 13
            color: Theme.warnFg
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            Text {
                text: model.fullName
                font.family: Theme.fontUi
                font.pixelSize: Theme.fontSm
                color: Theme.textPrimary
            }
            Text {
                text: model.address
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }
        }
    }
}
