import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../dialogs"

// Req 31 System Information: four tabs of key/value details, Refresh, Copy All.
Card {
    id: root
    width: 700
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias tabs: tabs
    property alias grid: grid
    property alias statusLabel: statusLabel
    property alias refreshButton: refreshButton
    property alias copyButton: copyButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader {
            title: "System information"
            meta: "refreshes when a DUT connects"
            Layout.fillWidth: true
            AppButton { id: refreshButton; objectName: "sysInfoRefreshButton"; text: "Refresh"; iconName: "refresh"; small: true }
            AppButton { id: copyButton; objectName: "sysInfoCopyButton"; text: "Copy all"; iconName: "copy"; small: true }
        }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10
            SegmentedControl {
                id: tabs
                objectName: "sysInfoTabs"
                model: ["Chip Information", "Device Information", "RPC Information", "Firmware/Application"]
                small: true
            }
            KeyValueGrid {
                id: grid
                objectName: "sysInfoGrid"
                monoValues: true
                Layout.fillWidth: true
            }
            Text {
                id: statusLabel
                objectName: "sysInfoStatus"
                text: "DUT 1 · EFR32XG29XFULL revA0"
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }
        }
    }
}
