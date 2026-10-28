import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 27 GFSK Packet Generator: modulation (symbol rate, deviation, BT), frequency, power, payload,
// Generate code, Add to Actions.
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias rateField: rateField
    property alias deviationField: deviationField
    property alias indexLabel: indexLabel
    property alias btField: btField
    property alias freqField: freqField
    property alias powerField: powerField
    property alias payloadCombo: payloadCombo
    property alias lengthField: lengthField
    property alias errorLabel: errorLabel
    property alias generateButton: generateButton
    property alias addButton: addButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "GFSK packet"; meta: "self-contained code for the signal generator"; Layout.fillWidth: true }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 6
                Layout.fillWidth: true

                Text { text: "Symbol rate (kbps)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: rateField; objectName: "gfskRateField"; mono: true; selectOnFocus: true; placeholderText: "1000"; Layout.preferredWidth: 100 }
                Text { text: "Deviation (kHz)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                RowLayout {
                    spacing: 6
                    AppTextField { id: deviationField; objectName: "gfskDeviationField"; mono: true; selectOnFocus: true; placeholderText: "250"; Layout.preferredWidth: 80 }
                    Text { id: indexLabel; objectName: "gfskIndex"; text: "h = 0.5"; font.family: Theme.fontMono; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                }

                Text { text: "BT"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: btField; objectName: "gfskBtField"; mono: true; selectOnFocus: true; placeholderText: "0.5"; Layout.preferredWidth: 100 }
                Text { text: "Frequency (MHz)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: freqField; objectName: "gfskFrequencyField"; mono: true; selectOnFocus: true; placeholderText: "2440"; Layout.preferredWidth: 80 }

                Text { text: "Power (dBm)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppTextField { id: powerField; objectName: "gfskPowerField"; mono: true; selectOnFocus: true; placeholderText: "0"; Layout.preferredWidth: 100 }
                Text { text: "Payload"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                RowLayout {
                    spacing: 6
                    AppComboBox { id: payloadCombo; objectName: "gfskPayloadCombo"; implicitHeight: 28; Layout.preferredWidth: 90 }
                    AppTextField { id: lengthField; objectName: "gfskLengthField"; mono: true; selectOnFocus: true; placeholderText: "37"; Layout.preferredWidth: 50 }
                    Text { text: "bytes"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                }
            }
            Text { id: errorLabel; objectName: "gfskErrors"; text: ""; visible: text !== ""; font.pixelSize: Theme.fontXs; color: Theme.dangerFg; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                spacing: 8
                AppButton { id: generateButton; objectName: "gfskGenerateButton"; text: "Generate code"; iconName: "code"; variant: "primary" }
                AppButton { id: addButton; objectName: "gfskAddToActionsButton"; text: "Add to Actions"; iconName: "bolt" }
            }
        }
    }
}
