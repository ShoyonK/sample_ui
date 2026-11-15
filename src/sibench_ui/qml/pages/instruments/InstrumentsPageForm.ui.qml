import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../shell"

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
                ToolSlot { toolKey: "siggen"; Layout.fillWidth: true }
                ToolSlot { toolKey: "blePacket"; Layout.fillWidth: true }
                ToolSlot { toolKey: "gfsk"; Layout.fillWidth: true }
            }
            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                Layout.preferredWidth: 600
                spacing: 10
                ToolSlot { toolKey: "rfSwitch"; Layout.fillWidth: true }
                ToolSlot { toolKey: "chamber"; Layout.fillWidth: true }
            }
        }
        ToolSlot { toolKey: "eca"; Layout.fillWidth: true }
    }
}
