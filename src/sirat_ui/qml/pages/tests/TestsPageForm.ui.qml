import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 33 Test Execution: test selection on the left; progress, results, output and the Run / Stop /
// Export Results buttons on the right.
RowLayout {
    id: root
    width: 1500
    height: 760
    spacing: 10

    property alias testList: testList
    property alias listMessage: listMessage
    property alias statusChip: statusChip
    property alias runButton: runButton
    property alias stopButton: stopButton
    property alias exportButton: exportButton
    property alias progressBar: progressBar
    property alias currentLabel: currentLabel
    property alias elapsedLabel: elapsedLabel
    property alias resultList: resultList
    property alias emptyResults: emptyResults
    property alias output: output
    // Column widths shared by the results header and TestResultRow; Notes takes the rest.
    readonly property var resultColumns: ({ num: 24, name: 220, status: 56, started: 72, duration: 52 })

    Card {
        Layout.preferredWidth: 320
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                title: "Tests"
                Layout.fillWidth: true
            }
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ListView {
                    id: testList
                    objectName: "testList"
                    anchors.fill: parent
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: AppScrollBar {}
                    delegate: TestListRow {}
                }
                Text {
                    id: listMessage
                    objectName: "testListMessage"
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.s4
                    text: "No tests to run"
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Item {
                Layout.fillWidth: true
                implicitHeight: Theme.headerHeight
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s3
                    anchors.rightMargin: Theme.s3
                    spacing: Theme.s2
                    Text {
                        text: "Test execution"
                        font.pixelSize: Theme.fontMd
                        font.weight: Font.DemiBold
                        color: Theme.textPrimary
                    }
                    Chip { id: statusChip; objectName: "testRunStatus"; text: "Running · test 2 of 4"; tone: "info" }
                    Item { Layout.fillWidth: true }
                    AppButton { id: runButton; objectName: "runTestsButton"; text: "Run"; iconName: "play"; small: true; variant: "run" }
                    AppButton { id: stopButton; objectName: "stopTestsButton"; text: "Stop"; iconName: "stop"; small: true; variant: "danger" }
                    AppButton { id: exportButton; objectName: "exportTestResultsButton"; text: "Export results"; iconName: "save"; small: true }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            }

            Column {
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 6
                RowLayout {
                    width: parent.width
                    Text {
                        id: currentLabel
                        objectName: "currentTestLabel"
                        text: "Current test: Sample test 2"
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    Text {
                        id: elapsedLabel
                        objectName: "testElapsedLabel"
                        text: "0:04"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }
                Rectangle {
                    width: parent.width
                    height: 6
                    radius: 3
                    color: Theme.select
                    Rectangle {
                        id: progressBar
                        objectName: "testProgress"
                        width: parent.width * 0.25
                        height: parent.height
                        radius: 3
                        color: Theme.textPrimary
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 14
                Layout.rightMargin: 14
                Layout.topMargin: Theme.s2
                Layout.bottomMargin: Theme.s2
                spacing: 10
                Text { text: ""; Layout.preferredWidth: root.resultColumns.num }
                Text { text: "Test"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: root.resultColumns.name }
                Text { text: "Status"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: root.resultColumns.status }
                Text { text: "Notes"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.fillWidth: true }
                Text { text: "Started"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; Layout.preferredWidth: root.resultColumns.started }
                Text { text: "Duration"; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.textMuted; horizontalAlignment: Text.AlignRight; Layout.preferredWidth: root.resultColumns.duration }
            }
            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ListView {
                    id: resultList
                    objectName: "testResultList"
                    anchors.fill: parent
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: AppScrollBar {}
                    delegate: TestResultRow { columns: root.resultColumns }
                }
                EmptyState {
                    id: emptyResults
                    anchors.centerIn: parent
                    iconName: "flask"
                    title: "No results yet"
                    body: "Check the tests to run and press Run."
                }
            }

            ConsolePanel {
                id: output
                objectName: "testOutput"
                title: "Output"
                clearable: false
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                Layout.margins: Theme.s2
            }
        }
    }
}
