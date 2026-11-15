import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../shell"

// Radio and PHY: Load LPW PHY and PRS signal routing on the left (req 23, req 24), WiFi PHY on the right (req 23).
ScrollView {
    id: root
    width: 1500
    height: 760
    clip: true
    contentWidth: availableWidth

    RowLayout {
        width: root.availableWidth
        spacing: 10

        ColumnLayout {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: 560
            Layout.maximumWidth: 600
            spacing: 10
            LpwPhyCard { Layout.fillWidth: true }
            ToolSlot { toolKey: "prs"; Layout.fillWidth: true }
        }
        ToolSlot {
            toolKey: "wifiPhy"
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: true
        }
    }
}
