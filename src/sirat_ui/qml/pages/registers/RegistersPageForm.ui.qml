import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../theme"

SplitView {
    id: root
    width: 1500
    height: 760
    orientation: Qt.Horizontal

    property alias tree: tree
    property alias favorites: favorites
    property alias detail: detail

    handle: Item {
        implicitWidth: 10
    }

    PeripheralTree {
        id: tree
        SplitView.preferredWidth: 360
        SplitView.minimumWidth: 260
    }

    FavoritesPanel {
        id: favorites
        SplitView.preferredWidth: 190
        SplitView.minimumWidth: 150
    }

    RegisterDetail {
        id: detail
        SplitView.fillWidth: true
        SplitView.minimumWidth: 560
    }
}
