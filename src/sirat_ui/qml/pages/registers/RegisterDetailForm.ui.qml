import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Register mode: header, value bar, bit grid, fields table. Peripheral and empty modes below.
Item {
    id: root
    width: 960
    height: 760

    property string mode: "register"
    property alias titleLabel: titleLabel
    property alias favoriteButton: favoriteButton
    property alias accessChip: accessChip
    property alias metaLabel: metaLabel
    property alias chipLabel: chipLabel
    property alias descriptionLabel: descriptionLabel
    property alias valueField: valueField
    property alias formatControl: formatControl
    property alias readButton: readButton
    property alias writeButton: writeButton
    property alias bitValueLabel: bitValueLabel
    property alias bitGrid: bitGrid
    property alias fieldsCountChip: fieldsCountChip
    property alias fieldsTable: fieldsTable
    property alias saveActionButton: saveActionButton
    property alias peripheralTitle: peripheralTitle
    property alias peripheralBody: peripheralBody
    property alias readPeripheralButton: readPeripheralButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        visible: root.mode === "register"

        Card {
            Layout.fillWidth: true
            implicitHeight: 64
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                spacing: 10
                Text {
                    id: titleLabel
                    objectName: "detailTitle"
                    text: "BUFC.LPMODE"
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontTitle
                    font.weight: Font.Bold
                    color: Theme.textPrimary
                }
                IconButton {
                    id: favoriteButton
                    objectName: "favoriteButton"
                    iconName: "star"
                    iconColor: Theme.warnFg
                    tip: "Add to favorites"
                }
                Chip {
                    id: accessChip
                    text: "Read/Write"
                    tone: "ok"
                }
                Text {
                    id: metaLabel
                    text: "0xBA000008 · 32-bit · reset 0x00000000"
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Column {
                    Layout.alignment: Qt.AlignVCenter
                    Text {
                        id: chipLabel
                        anchors.right: parent.right
                        text: "LION A0"
                        font.family: Theme.fontUi
                        font.pixelSize: Theme.fontXs
                        color: Theme.textMuted
                    }
                    Text {
                        id: descriptionLabel
                        anchors.right: parent.right
                        text: "Low power mode"
                        font.family: Theme.fontUi
                        font.pixelSize: Theme.fontMd
                        color: Theme.textPrimary
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true
            implicitHeight: 56
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                spacing: Theme.s2
                Text {
                    text: "Value"
                    font.pixelSize: Theme.fontSm
                    color: Theme.textMuted
                    Layout.preferredWidth: 42
                }
                AppTextField {
                    id: valueField
                    objectName: "registerValueField"
                    mono: true
                    implicitHeight: 32
                    font.pixelSize: Theme.fontValue
                    placeholderText: "<not read yet - click \"Read\">"
                    Layout.fillWidth: true
                }
                SegmentedControl {
                    id: formatControl
                    objectName: "formatControl"
                    model: ["Hex", "Dec", "Bin"]
                }
                AppButton {
                    id: readButton
                    objectName: "readButton"
                    text: "Read"
                    iconName: "download"
                }
                AppButton {
                    id: writeButton
                    objectName: "writeButton"
                    text: "Write"
                    iconName: "upload"
                    variant: "primary"
                }
            }
        }

        Card {
            Layout.fillWidth: true
            implicitHeight: bitGrid.implicitHeight + Theme.headerHeight + 26
            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                CardHeader {
                    title: "Bit pattern"
                    meta: "click a bit to write it · underline marks a field"
                    Layout.fillWidth: true
                    Text {
                        id: bitValueLabel
                        text: "0x00000003"
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }
                BitGrid {
                    id: bitGrid
                    objectName: "bitGrid"
                    Layout.fillWidth: true
                    Layout.margins: 14
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
                    title: "Fields"
                    meta: "double-click a value to edit · Enter writes"
                    Layout.fillWidth: true
                    Chip {
                        id: fieldsCountChip
                        text: "2 fields"
                    }
                }
                FieldsTable {
                    id: fieldsTable
                    objectName: "fieldsTable"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.margins: Theme.s2
                    Item { Layout.fillWidth: true }
                    AppButton {
                        id: saveActionButton
                        objectName: "saveToActionsButton"
                        text: "Save register to actions"
                        iconName: "save"
                        small: true
                    }
                }
            }
        }
    }

    Card {
        anchors.fill: parent
        visible: root.mode === "peripheral"
        Column {
            anchors.centerIn: parent
            spacing: Theme.s3
            Text {
                id: peripheralTitle
                anchors.horizontalCenter: parent.horizontalCenter
                text: "BUFC"
                font.family: Theme.fontMono
                font.pixelSize: Theme.fontDisplay
                font.weight: Font.Bold
                color: Theme.textPrimary
            }
            Text {
                id: peripheralBody
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Buffer controller · 10 registers"
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
            }
            AppButton {
                id: readPeripheralButton
                objectName: "readPeripheralButton"
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Read all registers"
                iconName: "download"
                variant: "primary"
            }
        }
    }

    Card {
        anchors.fill: parent
        visible: root.mode === "empty"
        EmptyState {
            anchors.centerIn: parent
            iconName: "cpu"
            title: "Pick a register"
            body: "Choose a peripheral or register in the tree, or search by name. Fields and bits show up here."
        }
    }
}
