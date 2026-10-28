import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 22 DUT Control API Explorer: the API tree with a filter on the left; the method's signature and
// docstring, its parameter form (Execute, Add to Actions) and the results on the right.
RowLayout {
    id: root
    width: 1200
    height: 700
    spacing: 10

    property alias reloadButton: reloadButton
    property alias collapseButton: collapseButton
    property alias filterField: filterField
    property alias treeList: treeList
    property alias treeEmpty: treeEmpty
    property alias methodHeader: methodHeader
    property alias signatureLabel: signatureLabel
    property alias docLabel: docLabel
    property alias formatHint: formatHint
    property alias paramList: paramList
    property alias noParams: noParams
    property alias problemLabel: problemLabel
    property alias executeButton: executeButton
    property alias addButton: addButton
    property alias details: details
    property alias noMethod: noMethod
    property alias output: output

    Card {
        Layout.preferredWidth: 360
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 0
            CardHeader {
                title: "DUT control API"
                Layout.fillWidth: true
                IconButton { id: collapseButton; objectName: "apiCollapseButton"; iconName: "fold"; tip: "Collapse all" }
                IconButton { id: reloadButton; objectName: "apiReloadButton"; iconName: "refresh"; tip: "Reload the API from the DUT" }
            }
            AppTextField {
                id: filterField
                objectName: "apiFilterField"
                leadingIcon: "search"
                placeholderText: "Filter methods (e.g. power)"
                Layout.fillWidth: true
                Layout.margins: Theme.s2
            }
            ListView {
                id: treeList
                objectName: "apiTree"
                clip: true
                Layout.fillWidth: true
                Layout.fillHeight: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: ApiTreeRow {}
                Text {
                    id: treeEmpty
                    anchors.centerIn: parent
                    width: parent.width - 40
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                }
            }
        }
    }

    ColumnLayout {
        spacing: 10
        Layout.fillWidth: true
        Layout.fillHeight: true

        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 3
            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                CardHeader {
                    id: methodHeader
                    title: "Method"
                    monoTitle: true
                    Layout.fillWidth: true
                    AppButton { id: addButton; objectName: "apiAddToActionsButton"; text: "Add to Actions"; iconName: "bolt"; small: true }
                    AppButton { id: executeButton; objectName: "apiExecuteButton"; text: "Execute"; iconName: "play"; small: true; variant: "primary" }
                }
                ScrollView {
                    id: detailScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    padding: Theme.s4
                    contentWidth: availableWidth
                    clip: true
                    ColumnLayout {
                        id: details
                        width: detailScroll.availableWidth
                        spacing: Theme.s2
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: signatureLabel.implicitHeight + 14
                            radius: Theme.radiusSm
                            color: Theme.surface2
                            border.color: Theme.border
                            TextEdit {
                                id: signatureLabel
                                objectName: "apiSignature"
                                x: 7
                                y: 7
                                width: parent.width - 14
                                readOnly: true
                                selectByMouse: true
                                wrapMode: TextEdit.WrapAnywhere
                                font.family: Theme.fontMono
                                font.pixelSize: Theme.fontSm
                                color: Theme.textPrimary
                            }
                        }
                        Text {
                            id: docLabel
                            wrapMode: Text.WordWrap
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }
                        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border; Layout.topMargin: 4 }
                        Text { text: "Parameters"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary }
                        ColumnLayout {
                            id: paramList
                            objectName: "apiParams"
                            spacing: 6
                            Layout.fillWidth: true
                        }
                        Text { id: noParams; text: "This method takes no parameters."; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
                        Text {
                            id: formatHint
                            wrapMode: Text.WordWrap
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }
                        Text {
                            id: problemLabel
                            objectName: "apiProblems"
                            visible: text !== ""
                            font.pixelSize: Theme.fontXs
                            color: Theme.dangerFg
                            Layout.fillWidth: true
                        }
                    }
                }
            }
            EmptyState {
                id: noMethod
                anchors.centerIn: parent
                anchors.verticalCenterOffset: 16
                iconName: "bolt"
                title: "Pick a method"
                body: "Its signature, docstring and parameters show here."
            }
        }

        OutputView {
            id: output
            prefix: "api"
            title: "Results"
            emptyText: "Results, errors and hints for common failures appear here."
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 2
        }
    }
}
