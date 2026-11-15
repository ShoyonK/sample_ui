import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

Card {
    id: root
    width: 190
    height: 760

    property alias header: header
    property alias list: list

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            id: header
            title: "Favorites"
            Layout.fillWidth: true
        }

        ListView {
            id: list
            objectName: "favoritesList"
            clip: true
            spacing: 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 6
            boundsBehavior: Flickable.StopAtBounds
            delegate: FavoriteRow {}
        }
    }
}
