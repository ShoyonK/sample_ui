import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../dialogs"

// Settings: preferences, user settings (req 2), About (req 2) | hardware configuration (req 32),
// system information (req 31).
ScrollView {
    id: root
    width: 1500
    height: 760
    clip: true
    contentWidth: availableWidth

    property alias darkModeBox: darkModeBox
    property alias autoReadBox: autoReadBox
    property alias confirmBox: confirmBox
    property alias secureBox: secureBox
    property alias clearCacheButton: clearCacheButton
    property alias exportButton: exportButton
    property alias importButton: importButton
    property alias clearAllButton: clearAllButton
    property alias aboutGrid: aboutGrid
    property alias saveSessionButton: saveSessionButton
    property alias loadSessionButton: loadSessionButton
    property alias autosaveLabel: autosaveLabel
    property alias shortcutRepeater: shortcutRepeater

    RowLayout {
        width: root.availableWidth
        spacing: 10

        ColumnLayout {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: 1
            Layout.fillWidth: true
            spacing: 10

            Card {
                Layout.fillWidth: true
                implicitHeight: prefsColumn.implicitHeight + Theme.headerHeight + 28
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    CardHeader { title: "Preferences"; meta: "saved to ~/.sirat/preferences.json"; Layout.fillWidth: true }
                    ColumnLayout {
                        id: prefsColumn
                        Layout.margins: Theme.s4
                        spacing: 14
                        AppCheckBox { id: darkModeBox; objectName: "darkModeBox"; text: "Dark mode" }
                        AppCheckBox { id: autoReadBox; objectName: "autoReadBox"; text: "Auto-read register on click" }
                        AppCheckBox { id: confirmBox; objectName: "confirmCriticalBox"; text: "Confirm writes to critical peripherals (CMU, EMU, MSC, SMU)" }
                        AppCheckBox { id: secureBox; objectName: "showSecureBox"; text: "Show peripherals with _NS/_S" }
                        AppButton { id: clearCacheButton; objectName: "clearCacheButton"; text: "Clear register cache"; iconName: "erase" }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                implicitHeight: userColumn.implicitHeight + Theme.headerHeight + 28
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    CardHeader { title: "User settings"; meta: "favorites, notes, formulas, actions, sequences, watch, logger, preferences, hardware"; Layout.fillWidth: true }
                    ColumnLayout {
                        id: userColumn
                        Layout.margins: Theme.s4
                        Layout.fillWidth: true
                        spacing: 10
                        Text {
                            text: "Export saves everything to one JSON file you can import on another station. Clear resets everything to defaults."
                            wrapMode: Text.WordWrap
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }
                        Row {
                            spacing: 8
                            AppButton { id: exportButton; objectName: "exportSettingsButton"; text: "Export…"; iconName: "upload" }
                            AppButton { id: importButton; objectName: "importSettingsButton"; text: "Import…"; iconName: "download" }
                            AppButton { id: clearAllButton; objectName: "clearAllSettingsButton"; text: "Clear all…"; iconName: "delete"; variant: "danger" }
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                implicitHeight: sessionColumn.implicitHeight + Theme.headerHeight + 28
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    CardHeader { title: "Sessions"; meta: "saved to ~/.sirat/sessions"; Layout.fillWidth: true }
                    ColumnLayout {
                        id: sessionColumn
                        Layout.margins: Theme.s4
                        Layout.fillWidth: true
                        spacing: 10
                        Text {
                            text: "A session saves your notes, formulas, actions, favorites and operation history under a name, so you can come back to a piece of work later."
                            wrapMode: Text.WordWrap
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            spacing: 8
                            AppButton { id: saveSessionButton; objectName: "saveSessionButton"; text: "Save session…"; iconName: "save" }
                            AppButton { id: loadSessionButton; objectName: "loadSessionButton"; text: "Load session…"; iconName: "download" }
                            Text {
                                id: autosaveLabel
                                objectName: "autosaveLabel"
                                text: "Auto-saves every 5 minutes"
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                                Layout.leftMargin: 6
                            }
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                implicitHeight: shortcutGrid.implicitHeight + Theme.headerHeight + 32
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    CardHeader { title: "Keyboard shortcuts"; meta: "also shown in Ctrl+K and in button tooltips"; Layout.fillWidth: true }
                    GridLayout {
                        id: shortcutGrid
                        objectName: "shortcutGuide"
                        columns: 2
                        columnSpacing: Theme.s3
                        rowSpacing: 6
                        Layout.fillWidth: true
                        Layout.margins: Theme.s4
                        Repeater {
                            id: shortcutRepeater
                            model: [{ keys: "Ctrl+K", title: "Open the command palette" }]
                            delegate: Item {
                                Layout.columnSpan: 1
                                Layout.fillWidth: true
                                implicitHeight: 24
                                Rectangle {
                                    id: keyChip
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 64
                                    height: 20
                                    radius: Theme.radiusSm
                                    color: Theme.surface2
                                    border.color: Theme.borderStrong
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.keys
                                        font.family: Theme.fontMono
                                        font.pixelSize: Theme.fontXs
                                        color: Theme.textPrimary
                                    }
                                }
                                Text {
                                    anchors.left: keyChip.right
                                    anchors.leftMargin: Theme.s2
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.title
                                    elide: Text.ElideRight
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textPrimary
                                }
                            }
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                implicitHeight: aboutGrid.implicitHeight + Theme.headerHeight + 32
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    CardHeader { title: "About SiRAT"; meta: "Silicon Labs Register Access Tool"; Layout.fillWidth: true }
                    KeyValueGrid {
                        id: aboutGrid
                        objectName: "aboutGrid"
                        monoValues: true
                        Layout.fillWidth: true
                        Layout.margins: Theme.s4
                    }
                }
            }
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: 1
            Layout.fillWidth: true
            spacing: 10

            HardwareConfigCard {
                Layout.fillWidth: true
            }
            SystemInfoCard {
                Layout.fillWidth: true
            }
        }
    }
}
