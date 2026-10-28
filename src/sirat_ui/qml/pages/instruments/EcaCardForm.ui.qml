import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 30 ECA Capture: channels, trigger and capture parameters, Start capture; one plot per channel (drag to
// zoom, double-click to reset) with the trigger and markers A/B; timing measurements; Save CSV.
Card {
    id: root
    width: 1200
    implicitHeight: body.implicitHeight + Theme.headerHeight + 28

    property alias status: status
    property alias channelRepeater: channelRepeater
    property alias triggerCombo: triggerCombo
    property alias edgeControl: edgeControl
    property alias rateField: rateField
    property alias durationField: durationField
    property alias pretriggerField: pretriggerField
    property alias samplesLabel: samplesLabel
    property alias errorLabel: errorLabel
    property alias captureButton: captureButton
    property alias stopButton: stopButton
    property alias progressLabel: progressLabel
    property alias plotRepeater: plotRepeater
    property alias plotsEmpty: plotsEmpty
    property alias markerAField: markerAField
    property alias markerBField: markerBField
    property alias markerLabel: markerLabel
    property alias resetZoomButton: resetZoomButton
    property alias saveButton: saveButton
    property alias measureList: measureList
    property alias analysis: analysis

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "ECA capture"; meta: "capture, plot and measure timing signals"; Layout.fillWidth: true }
        RowLayout {
            id: body
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 18

            // ---- configuration
            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: 300
                Layout.maximumWidth: 300
                spacing: 8

                InstrumentStatus { id: status; prefix: "eca"; Layout.fillWidth: true }

                Text { text: "Channels"; font.pixelSize: Theme.fontXs; color: Theme.textMuted; Layout.topMargin: 2 }
                Flow {
                    spacing: 10
                    Layout.fillWidth: true
                    Repeater { id: channelRepeater }
                }

                GridLayout {
                    columns: 2
                    columnSpacing: 10
                    rowSpacing: 6
                    Layout.fillWidth: true
                    Text { text: "Trigger"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                    AppComboBox { id: triggerCombo; objectName: "ecaTriggerCombo"; implicitHeight: 28; Layout.fillWidth: true }
                    Text { text: "Edge"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                    SegmentedControl { id: edgeControl; objectName: "ecaEdgeControl"; small: true; model: ["Rising", "Falling", "Either"] }
                    Text { text: "Sample rate (MHz)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                    AppTextField { id: rateField; objectName: "ecaRateField"; mono: true; selectOnFocus: true; placeholderText: "1"; Layout.preferredWidth: 90 }
                    Text { text: "Duration (ms)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                    AppTextField { id: durationField; objectName: "ecaDurationField"; mono: true; selectOnFocus: true; placeholderText: "5"; Layout.preferredWidth: 90 }
                    Text { text: "Pre-trigger (%)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                    AppTextField { id: pretriggerField; objectName: "ecaPretriggerField"; mono: true; selectOnFocus: true; placeholderText: "10"; Layout.preferredWidth: 90 }
                }
                Text { id: samplesLabel; objectName: "ecaSamples"; text: ""; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                Text { id: errorLabel; objectName: "ecaErrors"; text: ""; visible: text !== ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    spacing: 8
                    AppButton { id: captureButton; objectName: "ecaCaptureButton"; text: "Start capture"; iconName: "play"; variant: "primary" }
                    AppButton { id: stopButton; objectName: "ecaStopButton"; text: "Stop"; iconName: "stop"; variant: "danger" }
                }
                Text { id: progressLabel; objectName: "ecaProgress"; text: ""; font.pixelSize: Theme.fontXs; color: Theme.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }

            // ---- waveforms and analysis
            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                spacing: 8

                EmptyState {
                    id: plotsEmpty
                    objectName: "ecaEmpty"
                    iconName: "chart"
                    title: "No capture yet"
                    body: "Pick channels and a trigger, then Start capture. Drag across a plot to zoom; double-click to zoom out."
                    Layout.fillWidth: true
                    Layout.preferredHeight: 220
                }
                Repeater { id: plotRepeater }

                ColumnLayout {
                    id: analysis
                    spacing: 8
                    Layout.fillWidth: true
                    RowLayout {
                        spacing: 8
                        Layout.fillWidth: true
                        Text { text: "Marker A (ms)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                        AppTextField { id: markerAField; objectName: "ecaMarkerAField"; mono: true; selectOnFocus: true; placeholderText: "—"; Layout.preferredWidth: 80 }
                        Text { text: "B (ms)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                        AppTextField { id: markerBField; objectName: "ecaMarkerBField"; mono: true; selectOnFocus: true; placeholderText: "—"; Layout.preferredWidth: 80 }
                        Text { id: markerLabel; objectName: "ecaMarkerText"; text: ""; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; elide: Text.ElideRight; Layout.fillWidth: true }
                        AppButton { id: resetZoomButton; objectName: "ecaResetZoomButton"; text: "Zoom out"; iconName: "refresh"; small: true }
                        AppButton { id: saveButton; objectName: "ecaSaveButton"; text: "Save CSV…"; iconName: "save"; small: true }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 28
                        color: Theme.surface2
                        radius: Theme.radiusSm
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.s3
                            anchors.rightMargin: Theme.s3
                            spacing: Theme.s3
                            Text { text: "Channel"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 90 }
                            Text { text: "Range"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.fillWidth: true }
                            Text { text: "Mean"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 80 }
                            Text { text: "Rising edges"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 90 }
                            Text { text: "Frequency"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 90 }
                            Text { text: "High time"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 90 }
                            Text { text: "First rise"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 90 }
                        }
                    }
                    ListView {
                        id: measureList
                        objectName: "ecaMeasurements"
                        interactive: false
                        Layout.fillWidth: true
                        implicitHeight: contentHeight
                    }
                }
            }
        }
    }
}
