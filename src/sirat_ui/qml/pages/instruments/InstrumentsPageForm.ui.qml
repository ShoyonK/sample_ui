import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Instruments: the stimulus on the left (signal generator, BLE and GFSK packets, req 25-27), the bench on the
// right (RF switch, temperature chamber, req 28-29), and the measurement across the bottom (ECA, req 30).
ScrollView {
    id: root
    width: 1500
    height: 760
    clip: true
    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 10

        RowLayout {
            spacing: 10
            Layout.fillWidth: true

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                Layout.preferredWidth: 600
                spacing: 10
                SiggenCard { Layout.fillWidth: true }
                BlePacketCard { Layout.fillWidth: true }
                GfskCard { Layout.fillWidth: true }
            }
            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                Layout.preferredWidth: 600
                spacing: 10
                RfSwitchCard { Layout.fillWidth: true }
                ChamberCard { Layout.fillWidth: true }
            }
        }
        EcaCard { Layout.fillWidth: true }
    }
}
