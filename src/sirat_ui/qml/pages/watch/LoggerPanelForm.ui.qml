import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

Card {
    id: root
    width: 460
    height: 760

    property alias statusChip: statusChip
    property alias rateField: rateField
    property alias statusLabel: statusLabel
    property alias modeLabel: modeLabel
    property alias resetZoomButton: resetZoomButton
    property alias seriesList: seriesList
    property alias emptyState: emptyState
    property alias recordButton: recordButton
    property alias clearButton: clearButton
    property alias exportButton: exportButton
    property alias popOutButton: popOutButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            title: "Data logger"
            Layout.fillWidth: true
            Text { text: "Every"; height: 24; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            AppTextField {
                id: rateField
                objectName: "loggerRateField"
                Accessible.name: "Sample interval in seconds"
                mono: true
                selectOnFocus: true
                width: 64
                implicitHeight: 24
                text: "0.5"
            }
            Text { text: "s"; height: 24; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            Chip { id: statusChip; text: "Recording"; tone: "ok"; y: 2 }
            IconButton { id: popOutButton; objectName: "loggerPopOutButton"; iconName: "export"; tip: "Open the data logger in its own window" }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Theme.s3
            Layout.leftMargin: Theme.s3
            Layout.rightMargin: Theme.s3
            spacing: Theme.s2
            Column {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    id: statusLabel
                    objectName: "loggerStatus"
                    text: "Recording · 1,284 samples · 10:42.0 elapsed"
                    font.pixelSize: Theme.fontSm
                    color: Theme.textPrimary
                }
                Text {
                    id: modeLabel
                    text: "Source: station watch · drag on a plot to zoom, double-click to reset"
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    width: parent.width
                }
            }
            AppButton {
                id: resetZoomButton
                objectName: "loggerResetZoomButton"
                text: "Reset zoom"
                small: true
                variant: "ghost"
            }
        }

        ListView {
            id: seriesList
            objectName: "loggerSeriesList"
            clip: true
            spacing: Theme.s3
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.s3
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: AppScrollBar {}
            delegate: SeriesRow {}

            EmptyState {
                id: emptyState
                anchors.centerIn: parent
                visible: false
                iconName: "chart"
                title: "No fields logged"
                body: "Use the chart button on a field in the register view, or Add all to logger."
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.s2
            AppButton { id: recordButton; objectName: "loggerRecordButton"; text: "Stop"; iconName: "stop"; small: true }
            AppButton { id: clearButton; objectName: "loggerClearButton"; text: "Clear data"; small: true; variant: "ghost" }
            Item { Layout.fillWidth: true }
            AppButton { id: exportButton; objectName: "loggerExportButton"; text: "Export CSV"; iconName: "save"; small: true }
        }
    }
}
