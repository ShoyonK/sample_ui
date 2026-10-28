import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 23 WiFi PHY Configuration: live packet visualizer, RX/TX, basic parameters, TX parameters (TX only),
// advanced parameters (802.11ax/be only), Apply Configuration, Add to Actions.
Card {
    id: root
    width: 900
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias phyChip: phyChip
    property alias unavailableBanner: unavailableBanner
    property alias unavailableLabel: unavailableLabel
    property alias visualizer: visualizer
    property alias modeControl: modeControl
    property alias standardCombo: standardCombo
    property alias channelCombo: channelCombo
    property alias powerCombo: powerCombo
    property alias rateCombo: rateCombo
    property alias txSection: txSection
    property alias lengthField: lengthField
    property alias countField: countField
    property alias transmitCombo: transmitCombo
    property alias aggrBox: aggrBox
    property alias advancedSection: advancedSection
    property alias advancedBox: advancedBox
    property alias advancedGrid: advancedGrid
    property alias ppduCombo: ppduCombo
    property alias giCombo: giCombo
    property alias dcmBox: dcmBox
    property alias bandwidthCombo: bandwidthCombo
    property alias problemLabel: problemLabel
    property alias applyButton: applyButton
    property alias addButton: addButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader {
            title: "WiFi PHY configuration"
            meta: "Everest family"
            Layout.fillWidth: true
            Chip { id: phyChip; objectName: "wifiPhyName"; text: "WIFI_2p4G"; tone: "info"; mono: true }
        }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 12

            Rectangle {
                id: unavailableBanner
                Layout.fillWidth: true
                implicitHeight: 36
                radius: Theme.radiusSm
                color: Theme.warnBg
                Text {
                    id: unavailableLabel
                    objectName: "wifiUnavailable"
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.s3
                    text: "WiFi PHYs are for Everest-family chips. This DUT is Lion."
                    font.pixelSize: Theme.fontSm
                    color: Theme.warnFg
                }
            }

            PacketVisualizer { id: visualizer; objectName: "packetVisualizer"; Layout.fillWidth: true }

            RowLayout {
                spacing: 12
                Text { text: "Mode"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                SegmentedControl { id: modeControl; objectName: "wifiModeControl"; model: ["RX (receive)", "TX (transmit)"] }
            }

            Text { text: "Basic parameters"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary }
            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                Layout.fillWidth: true
                Text { text: "Standard"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                AppComboBox { id: standardCombo; objectName: "wifiStandardCombo"; implicitHeight: 28; Layout.fillWidth: true }
                Text { text: "Channel"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                AppComboBox { id: channelCombo; objectName: "wifiChannelCombo"; implicitHeight: 28; Layout.fillWidth: true }
                Text { text: "Power mode"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppComboBox { id: powerCombo; objectName: "wifiPowerCombo"; implicitHeight: 28; Layout.fillWidth: true }
                Text { text: "Rate / MCS"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                AppComboBox { id: rateCombo; objectName: "wifiRateCombo"; implicitHeight: 28; Layout.fillWidth: true }
            }

            ColumnLayout {
                id: txSection
                Layout.fillWidth: true
                spacing: 8
                Text { text: "TX parameters"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary }
                GridLayout {
                    columns: 4
                    columnSpacing: 12
                    rowSpacing: 8
                    Layout.fillWidth: true
                    Text { text: "Packet length"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                    AppTextField { id: lengthField; objectName: "wifiLengthField"; mono: true; selectOnFocus: true; placeholderText: "1-65535"; Layout.fillWidth: true }
                    Text { text: "Packets (0 = continuous)"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110; wrapMode: Text.WordWrap }
                    AppTextField { id: countField; objectName: "wifiCountField"; mono: true; selectOnFocus: true; placeholderText: "0-1000000"; Layout.fillWidth: true }
                    Text { text: "Transmit mode"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                    AppComboBox { id: transmitCombo; objectName: "wifiTransmitCombo"; implicitHeight: 28; Layout.fillWidth: true }
                    Item { Layout.preferredWidth: 1 }
                    AppCheckBox { id: aggrBox; objectName: "wifiAggrBox"; text: "Enable aggregation" }
                }
            }

            ColumnLayout {
                id: advancedSection
                Layout.fillWidth: true
                spacing: 8
                AppCheckBox { id: advancedBox; objectName: "wifiAdvancedBox"; text: "Advanced parameters (802.11ax/be)" }
                GridLayout {
                    id: advancedGrid
                    columns: 4
                    columnSpacing: 12
                    rowSpacing: 8
                    Layout.fillWidth: true
                    Text { text: "PPDU type"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                    AppComboBox { id: ppduCombo; objectName: "wifiPpduCombo"; implicitHeight: 28; Layout.fillWidth: true }
                    Text { text: "GI / LTF"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.preferredWidth: 110 }
                    AppComboBox { id: giCombo; objectName: "wifiGiCombo"; implicitHeight: 28; Layout.fillWidth: true }
                    Text { text: "Bandwidth"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                    AppComboBox { id: bandwidthCombo; objectName: "wifiBandwidthCombo"; implicitHeight: 28; Layout.fillWidth: true }
                    Item { Layout.preferredWidth: 1 }
                    AppCheckBox { id: dcmBox; objectName: "wifiDcmBox"; text: "Enable DCM" }
                }
            }

            Text {
                id: problemLabel
                objectName: "wifiProblems"
                text: ""
                font.pixelSize: Theme.fontXs
                color: Theme.dangerFg
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            RowLayout {
                spacing: 8
                AppButton { id: applyButton; objectName: "wifiApplyButton"; text: "Apply configuration"; iconName: "check"; variant: "primary" }
                AppButton { id: addButton; objectName: "wifiAddToActionsButton"; text: "Add to Actions"; iconName: "bolt" }
            }
        }
    }
}
