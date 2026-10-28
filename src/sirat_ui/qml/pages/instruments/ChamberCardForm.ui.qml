import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 29 Temperature Chamber Control: current temperature (large), setpoint, trend, Set Temperature,
// update interval, Wait for Stable with tolerance and hold time.
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias status: status
    property alias actualLabel: actualLabel
    property alias trendPill: trendPill
    property alias setpointLabel: setpointLabel
    property alias trendLine: trendLine
    property alias targetField: targetField
    property alias setButton: setButton
    property alias intervalField: intervalField
    property alias toleranceField: toleranceField
    property alias holdField: holdField
    property alias waitButton: waitButton
    property alias stopButton: stopButton
    property alias waitLabel: waitLabel
    property alias errorLabel: errorLabel

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "Temperature chamber"; meta: "settings aren't saved"; Layout.fillWidth: true }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10

            InstrumentStatus { id: status; prefix: "ch"; Layout.fillWidth: true }

            RowLayout {
                spacing: 14
                Layout.fillWidth: true
                ColumnLayout {
                    spacing: 2
                    Text {
                        id: actualLabel
                        objectName: "chActual"
                        text: "23.0 °C"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    RowLayout {
                        spacing: 6
                        StatusPill { id: trendPill; objectName: "chTrend"; text: "Stable"; level: "ok"; compact: true }
                        Text { id: setpointLabel; objectName: "chSetpoint"; text: "Setpoint 23 °C"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                    }
                }
                Sparkline {
                    id: trendLine
                    objectName: "chTrendLine"
                    lineColor: Theme.infoFg
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                }
            }

            GridLayout {
                columns: 3
                columnSpacing: 12
                rowSpacing: 6
                Layout.fillWidth: true

                Text { text: "Target (°C)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                AppTextField { id: targetField; objectName: "chTargetField"; mono: true; selectOnFocus: true; placeholderText: "25"; Layout.preferredWidth: 110 }
                AppButton { id: setButton; objectName: "chSetButton"; text: "Set temperature"; iconName: "check"; variant: "primary" }

                Text { text: "Update every (s)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: intervalField; objectName: "chIntervalField"; mono: true; selectOnFocus: true; placeholderText: "2"; Layout.preferredWidth: 110 }
                Item { Layout.fillWidth: true }
            }

            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border; Layout.topMargin: 2 }
            Text { text: "Wait for stable"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary }
            RowLayout {
                spacing: 8
                Text { text: "Within ±"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: toleranceField; objectName: "chToleranceField"; mono: true; selectOnFocus: true; placeholderText: "0.5"; Layout.preferredWidth: 60 }
                Text { text: "°C for"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: holdField; objectName: "chHoldField"; mono: true; selectOnFocus: true; placeholderText: "60"; Layout.preferredWidth: 60 }
                Text { text: "s"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppButton { id: waitButton; objectName: "chWaitButton"; text: "Wait for stable"; iconName: "pause" }
                AppButton { id: stopButton; objectName: "chStopButton"; text: "Stop"; iconName: "stop"; variant: "danger" }
            }
            Text { id: waitLabel; objectName: "chWaitText"; text: ""; visible: text !== ""; font.pixelSize: Theme.fontXs; color: Theme.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { id: errorLabel; objectName: "chErrors"; text: ""; visible: text !== ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }
}
