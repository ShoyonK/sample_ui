import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 18 Watch List: refresh rate, live/pause, add to logger, the watched fields. Can open in its own window.
Card {
    id: root
    width: 1000
    height: 760

    property alias intervalField: intervalField
    property alias livePill: livePill
    property alias liveButton: liveButton
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
            meta: "refresh every (s)"
            Layout.fillWidth: true
            AppTextField {
                id: intervalField
                objectName: "watchIntervalField"
                mono: true
                selectOnFocus: true
                width: 64
                implicitHeight: 24
                text: "1.0"
            }
            StatusPill { id: livePill; compact: true; text: "Live"; level: "ok" }
            AppButton { id: liveButton; objectName: "watchLiveButton"; text: "Pause"; iconName: "pause"; small: true }
            AppButton { id: refreshButton; objectName: "watchRefreshButton"; text: "Refresh once"; iconName: "refresh"; small: true }
            AppButton { id: deleteSelectedButton; objectName: "watchDeleteSelectedButton"; text: "Delete selected"; iconName: "delete"; small: true }
            AppButton { id: addSelectedButton; objectName: "watchAddSelectedButton"; text: "Add selected to logger"; iconName: "chart"; small: true }
            AppButton { id: addAllButton; objectName: "watchAddAllButton"; text: "Add all to logger"; iconName: "chart"; small: true; variant: "primary" }
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
