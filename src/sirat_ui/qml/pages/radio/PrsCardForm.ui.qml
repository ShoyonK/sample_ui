import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 24 PRS Signal Routing: family indicator, constraint text, signal / pin / channel, Apply Route,
// Add to Actions, and the active routes (Signal | Pin | PRS channel | Remove).
Card {
    id: root
    width: 560
    implicitHeight: column.implicitHeight + Theme.headerHeight + 28

    property alias sourceLabel: sourceLabel
    property alias signalCombo: signalCombo
    property alias pinCombo: pinCombo
    property alias channelCombo: channelCombo
    property alias hintLabel: hintLabel
    property alias applyButton: applyButton
    property alias addButton: addButton
    property alias routeList: routeList
    property alias routesEmpty: routesEmpty

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader { title: "PRS signal routing"; meta: "route an internal signal to a GPIO pin"; Layout.fillWidth: true }
        ColumnLayout {
            id: column
            Layout.margins: Theme.s4
            Layout.fillWidth: true
            spacing: 10
            Text {
                id: sourceLabel
                objectName: "prsSource"
                text: "Lion · dut_control_rta.series_six_lpw.lion.controls.pti_prs_module"
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            GridLayout {
                columns: 3
                columnSpacing: 10
                rowSpacing: 4
                Layout.fillWidth: true
                Text { text: "Signal"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                Text { text: "Pin"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                Text { text: "PRS channel"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                AppComboBox { id: signalCombo; objectName: "prsSignalCombo"; implicitHeight: 28; Layout.fillWidth: true; Layout.minimumWidth: 180 }
                AppComboBox { id: pinCombo; objectName: "prsPinCombo"; implicitHeight: 28; Layout.preferredWidth: 90 }
                AppComboBox { id: channelCombo; objectName: "prsChannelCombo"; implicitHeight: 28; Layout.preferredWidth: 90 }
            }
            Text {
                id: hintLabel
                objectName: "prsHint"
                text: "Port A uses channels 0-5"
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            RowLayout {
                spacing: 8
                AppButton { id: applyButton; objectName: "prsApplyButton"; text: "Apply route"; iconName: "play"; variant: "primary" }
                AppButton { id: addButton; objectName: "prsAddToActionsButton"; text: "Add to Actions"; iconName: "bolt" }
            }

            Text { text: "Active routes"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; Layout.topMargin: 4 }
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
                    Text { text: "Signal"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.fillWidth: true }
                    Text { text: "Pin"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 60 }
                    Text { text: "PRS channel"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 90 }
                    Item { Layout.preferredWidth: 86 }
                }
            }
            ListView {
                id: routeList
                objectName: "prsRouteList"
                interactive: false
                Layout.fillWidth: true
                implicitHeight: Math.max(contentHeight, 44)
                delegate: PrsRouteRow {}
                Text {
                    id: routesEmpty
                    anchors.centerIn: parent
                    text: "No routes yet. Routes aren't saved; add one to Actions to reuse it."
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }
            }
            Text {
                text: "Common signals: MODEM FRAMEDET, PREDET, TIMDET; RAC RX, TX, ACTIVE; SYNTH INLOCK."
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
                Layout.fillWidth: true
            }
        }
    }
}
