import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 21 results table header: click a column to sort by it, click again to reverse.
Rectangle {
    id: root
    property string sortColumn: ""
    property bool descending: false
    signal sortRequested(string column)

    readonly property var columns: [
        { key: "peripheral", title: "Peripheral", width: 120 },
        { key: "register", title: "Register", width: 160 },
        { key: "field", title: "Field", width: 170 },
        { key: "expected", title: "Expected", width: 200 },
        { key: "actual", title: "Actual", width: 220 },
        { key: "status", title: "Status", width: -1 }
    ]

    implicitHeight: 30
    color: Theme.surface2

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Repeater {
            model: root.columns
            delegate: Item {
                objectName: "radioSort_" + modelData.key
                Layout.preferredWidth: modelData.width > 0 ? modelData.width : -1
                Layout.fillWidth: modelData.width < 0
                Layout.fillHeight: true
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.sortRequested(modelData.key) }
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    Text {
                        text: modelData.title
                        font.pixelSize: Theme.fontXs
                        font.weight: Font.DemiBold
                        color: hover.hovered || root.sortColumn === modelData.key ? Theme.textPrimary : Theme.textMuted
                    }
                    Icon {
                        visible: root.sortColumn === modelData.key
                        name: root.descending ? "down" : "up"
                        size: 10
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }
}
