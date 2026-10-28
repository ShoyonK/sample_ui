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
    property alias fieldsTile: fieldsTile
    property alias samplesTile: samplesTile
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
            Chip { id: statusChip; text: "Recording"; tone: "ok" }
            IconButton { id: popOutButton; objectName: "loggerPopOutButton"; iconName: "export"; tip: "Open the data logger in its own window" }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.s3
            spacing: 10
            StatTile { id: fieldsTile; label: "Fields"; value: "2"; Layout.fillWidth: true }
            StatTile { id: samplesTile; label: "Samples"; value: "1,284"; Layout.fillWidth: true }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 64
                radius: Theme.radius
                color: Theme.surface2
                border.color: Theme.border
                Column {
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.s3
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text { text: "Sample rate (s)"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                    AppTextField {
                        id: rateField
                        objectName: "loggerRateField"
                        mono: true
                        selectOnFocus: true
                        width: 80
                        implicitHeight: 26
                        text: "0.5"
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
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
                    font.pixelSize: Theme.fontXs
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
