import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 12 Register Dumps: saved dumps on the left (Take a dump, Diff vs live, Compare); the comparison
// table on the right (Register | Before | After | Change, changed rows in light red, Save report).
// Req 21 Radio Calculator diff shares the right card: Peripheral | Register | Field | Expected | Actual | Status.
RowLayout {
    id: root
    width: 1500
    height: 760
    spacing: 10

    property alias folderHeader: folderHeader
    property alias takeButton: takeButton
    property alias fileList: fileList
    property alias filesEmpty: filesEmpty
    property alias diffLiveButton: diffLiveButton
    property alias compareWithButton: compareWithButton
    property alias compareFilesButton: compareFilesButton
    property alias deleteButton: deleteButton
    property alias resultHeader: resultHeader
    property alias saveReportButton: saveReportButton
    property alias clearButton: clearButton
    property alias summaryBanner: summaryBanner
    property alias summaryLabel: summaryLabel
    property alias summaryHelp: summaryHelp
    property alias columnHeader: columnHeader
    property alias beforeHeader: beforeHeader
    property alias afterHeader: afterHeader
    property alias rowList: rowList
    property alias resultEmpty: resultEmpty
    property alias radioButton: radioButton
    property alias radioHeader: radioHeader
    property alias radioList: radioList

    Card {
        Layout.preferredWidth: 380
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                id: folderHeader
                title: "Saved dumps"
                meta: "C:/temp/sirat/dumps"
                Layout.fillWidth: true
                AppButton { id: takeButton; objectName: "takeDumpButton"; text: "Take a dump…"; iconName: "download"; small: true; variant: "primary" }
            }
            ListView {
                id: fileList
                objectName: "dumpFileList"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: DumpFileRow {}
                EmptyState {
                    id: filesEmpty
                    anchors.centerIn: parent
                    iconName: "download"
                    title: "No dumps yet"
                    body: "Take a dump to save the registers of the peripherals you pick as a CSV file."
                }
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }
            Flow {
                Layout.fillWidth: true
                Layout.margins: Theme.s2
                spacing: 6
                AppButton { id: diffLiveButton; objectName: "diffLiveButton"; text: "Diff vs live"; iconName: "pulse"; small: true }
                AppButton { id: compareWithButton; objectName: "compareWithButton"; text: "Compare with…"; iconName: "compare"; small: true }
                AppButton { id: compareFilesButton; objectName: "compareFilesButton"; text: "Compare files…"; iconName: "upload"; small: true }
                AppButton { id: radioButton; objectName: "radioDiffButton"; text: "Radio Calculator diff…"; iconName: "antenna"; small: true }
                AppButton { id: deleteButton; objectName: "deleteDumpButton"; text: "Delete"; iconName: "delete"; small: true; variant: "ghost" }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                id: resultHeader
                title: "Register comparison"
                Layout.fillWidth: true
                AppButton { id: saveReportButton; objectName: "saveReportButton"; text: "Save report…"; iconName: "save"; small: true }
                AppButton { id: clearButton; objectName: "clearComparisonButton"; text: "Clear"; iconName: "erase"; small: true; variant: "ghost" }
            }
            Rectangle {
                id: summaryBanner
                Layout.fillWidth: true
                Layout.margins: Theme.s3
                implicitHeight: 36
                radius: Theme.radiusSm
                color: Theme.infoBg
                Text {
                    id: summaryLabel
                    objectName: "comparisonSummary"
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.s3
                    text: "3 registers differ · 120 compared"
                    font.pixelSize: Theme.fontSm
                    font.weight: Font.Bold
                    color: Theme.infoFg
                }
                HelpTip {
                    id: summaryHelp
                    objectName: "comparisonHelp"
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: summaryLabel.right
                    anchors.leftMargin: 10
                }
            }
            Rectangle {
                id: columnHeader
                Layout.fillWidth: true
                implicitHeight: 30
                color: Theme.surface2
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s3
                    anchors.rightMargin: Theme.s3
                    spacing: Theme.s3
                    Text { text: "Register"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 240 }
                    Text { id: beforeHeader; text: "Before"; elide: Text.ElideRight; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 190 }
                    Text { id: afterHeader; text: "After"; elide: Text.ElideRight; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: 190 }
                    Text { text: "Change"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.fillWidth: true }
                }
            }
            RadioHeader {
                id: radioHeader
                objectName: "radioHeader"
                Layout.fillWidth: true
            }
            ListView {
                id: radioList
                objectName: "radioRows"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: RadioRow {}
            }
            ListView {
                id: rowList
                objectName: "comparisonRows"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: DiffRow {}
                EmptyState {
                    id: resultEmpty
                    anchors.centerIn: parent
                    iconName: "compare"
                    title: "Nothing compared yet"
                    body: "Pick a saved dump, then use Diff vs live or Compare with."
                }
            }
        }
    }
}
