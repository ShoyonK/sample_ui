import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 25 Signal Generator: role status, type / waveform / frequency / power / overrides, Apply configuration,
// Load from instrument, Reload waveforms, Infinite and Single trigger, RF on/off, Add to Actions, code.
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias status: status
    property alias typeField: typeField
    property alias waveformCombo: waveformCombo
    property alias reloadButton: reloadButton
    property alias waveformHint: waveformHint
    property alias freqField: freqField
    property alias powerField: powerField
    property alias overridesField: overridesField
    property alias errorLabel: errorLabel
    property alias applyButton: applyButton
    property alias loadButton: loadButton
    property alias infiniteButton: infiniteButton
    property alias singleButton: singleButton
    property alias rfControl: rfControl
    property alias triggerLabel: triggerLabel
    property alias addButton: addButton
    property alias codeButton: codeButton
    property alias statusLabel: statusLabel

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "Signal generator"; meta: "saved to ~/.sirat/signal_generator.json"; Layout.fillWidth: true }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10

            InstrumentStatus { id: status; prefix: "sg"; Layout.fillWidth: true }

            GridLayout {
                columns: 2
                columnSpacing: 12
                rowSpacing: 6
                Layout.fillWidth: true

                Text { text: "Type"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                AppTextField { id: typeField; objectName: "sgTypeField"; mono: true; placeholderText: "PacketSrw"; Layout.preferredWidth: 200 }

                Text { text: "Waveform"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                RowLayout {
                    spacing: 6
                    AppComboBox { id: waveformCombo; objectName: "sgWaveformCombo"; implicitHeight: 28; Layout.preferredWidth: 200 }
                    IconButton { id: reloadButton; objectName: "sgReloadButton"; iconName: "refresh"; tip: "Reload waveforms (rescan the instrument's files)" }
                    Text { id: waveformHint; text: ""; font.pixelSize: Theme.fontXs; color: Theme.warnFg; elide: Text.ElideRight; Layout.fillWidth: true }
                }

                Text { text: "Frequency (MHz)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: freqField; objectName: "sgFrequencyField"; mono: true; selectOnFocus: true; placeholderText: "2440"; Layout.preferredWidth: 140 }

                Text { text: "Power (dBm)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: powerField; objectName: "sgPowerField"; mono: true; selectOnFocus: true; placeholderText: "0"; Layout.preferredWidth: 140 }

                Text { text: "Overrides"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: overridesField; objectName: "sgOverridesField"; mono: true; placeholderText: "KEY=value, KEY2=3"; Layout.fillWidth: true }
            }
            Text {
                id: errorLabel
                objectName: "sgErrors"
                text: ""
                visible: text !== ""
                font.pixelSize: Theme.fontXs
                color: Theme.dangerFg
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            RowLayout {
                spacing: 8
                AppButton { id: applyButton; objectName: "sgApplyButton"; text: "Apply configuration"; iconName: "upload"; variant: "primary" }
                AppButton { id: loadButton; objectName: "sgLoadButton"; text: "Load from instrument"; iconName: "download" }
            }

            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border; Layout.topMargin: 2 }
            Text { text: "Output"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary }
            RowLayout {
                spacing: 8
                SegmentedControl { id: rfControl; objectName: "sgRfControl"; model: ["RF off", "RF on"]; tones: ["", "ok"] }
                AppButton { id: infiniteButton; objectName: "sgInfiniteButton"; text: "Infinite trigger"; iconName: "play"; variant: "run" }
                AppButton { id: singleButton; objectName: "sgSingleButton"; text: "Single trigger"; iconName: "next" }
            }
            Text { id: triggerLabel; objectName: "sgTriggerText"; text: "Not triggered"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }

            RowLayout {
                spacing: 8
                Layout.topMargin: 2
                AppButton { id: addButton; objectName: "sgAddToActionsButton"; text: "Add to Actions"; iconName: "bolt" }
                AppButton { id: codeButton; objectName: "sgCodeButton"; text: "Code"; iconName: "code" }
                Text {
                    id: statusLabel
                    objectName: "sgStatus"
                    text: ""
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    Layout.leftMargin: 6
                }
            }
        }
    }
}
