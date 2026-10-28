import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 18 Watch List: refresh rate and Live | Paused, then actions. Selection actions appear only while rows are
// selected, so the toolbar shows what applies now. Can open in its own window.
Card {
    id: root
    width: 1000
    height: 760

    property alias intervalField: intervalField
    property alias liveToggle: liveToggle
    property alias densityToggle: densityToggle
    property alias selectionGroup: selectionGroup
    property alias selectionLabel: selectionLabel
    property alias refreshButton: refreshButton
    property alias addAllButton: addAllButton
    property alias addSelectedButton: addSelectedButton
    property alias deleteSelectedButton: deleteSelectedButton
    property alias clearButton: clearButton
    property alias popOutButton: popOutButton
    property alias list: list
    property alias emptyState: emptyState

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            title: "Watch list"
            Layout.fillWidth: true
            Text { text: "Every"; height: 24; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            AppTextField {
                id: intervalField
                objectName: "watchIntervalField"
                Accessible.name: "Refresh interval in seconds"
                mono: true
                selectOnFocus: true
                width: 64
                implicitHeight: 24
                text: "1.0"
            }
            Text { text: "s"; height: 24; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            SegmentedControl { id: liveToggle; objectName: "watchLiveToggle"; small: true; model: ["Live", "Paused"]; tones: ["ok", ""]; currentIndex: 1 }
            AppButton { id: refreshButton; objectName: "watchRefreshButton"; text: "Refresh once"; iconName: "refresh"; small: true }
            Rectangle { width: 1; height: 18; y: 3; color: Theme.border }
            Row {
                id: selectionGroup
                spacing: Theme.s2
                Text { id: selectionLabel; text: "2 selected"; font.pixelSize: Theme.fontSm; color: Theme.textPrimary; anchors.verticalCenter: parent.verticalCenter }
                AppButton { id: addSelectedButton; objectName: "watchAddSelectedButton"; text: "Add to logger"; iconName: "chart"; small: true }
                AppButton { id: deleteSelectedButton; objectName: "watchDeleteSelectedButton"; text: "Remove"; iconName: "delete"; small: true }
            }
            AppButton { id: addAllButton; objectName: "watchAddAllButton"; text: "Add all to logger"; iconName: "chart"; small: true; variant: "primary" }
            IconButton { id: densityToggle; objectName: "watchDensityToggle"; iconName: "textSize"; tip: "Large values, readable from the bench" }
            IconButton { id: clearButton; objectName: "watchClearButton"; iconName: "delete"; tip: "Clear all" }
            IconButton { id: popOutButton; objectName: "watchPopOutButton"; iconName: "export"; tip: "Open the watch list in its own window" }
        }

        Row {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.s3
            height: 30
            Repeater {
                model: [{ t: "Register / field", w: 0.3 }, { t: "Value", w: 0.12 }, { t: "Enum", w: 0.13 },
                        { t: "Calculated", w: 0.15 }, { t: "Changed", w: 0.1 }, { t: "Trend", w: 0.12 }]
                delegate: Text {
                    width: (list.width - 80) * modelData.w
                    height: 30
                    text: modelData.t
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Theme.fontXs
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

        ListView {
            id: list
            objectName: "watchList"
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: AppScrollBar {}
            delegate: WatchRow {}

            EmptyState {
                id: emptyState
                anchors.centerIn: parent
                visible: false
                iconName: "eye"
                title: "Nothing watched yet"
                body: "Use the eye button on a field in the register view to watch it here. Double-click a value to write it; Ctrl or Shift selects several rows."
            }
        }
    }
}
