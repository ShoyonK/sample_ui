import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One logged field's plot, filling its own window. Shares recording and zoom with the data logger.
Card {
    id: root
    property string fieldName: ""
    readonly property var vm: app.logger
    property int matches: 0

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader {
            title: root.fieldName
            monoTitle: true
            meta: root.vm.recording ? "recording" : "stopped"
            Layout.fillWidth: true
            AppButton {
                objectName: "graphResetZoom"
                text: "Reset zoom"
                small: true
                visible: root.vm.zoomStart >= 0
                onClicked: root.vm.resetZoom()
            }
            AppButton {
                objectName: "graphRecordButton"
                text: root.vm.recording ? "Stop" : "Start"
                iconName: root.vm.recording ? "stop" : "play"
                small: true
                enabled: root.vm.recording || root.vm.fieldCount > 0
                onClicked: root.vm.toggleRecording()
            }
        }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.s3
            Repeater {
                model: root.vm.series
                delegate: ColumnLayout {
                    visible: model.name === root.fieldName
                    anchors.fill: parent
                    spacing: 6
                    Component.onCompleted: if (visible) root.matches += 1
                    Component.onDestruction: if (visible) root.matches -= 1
                    Text {
                        text: model.lastText
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontXl
                        font.weight: Font.DemiBold
                        color: Theme.infoFg
                    }
                    TimePlot {
                        objectName: "graphPlot_" + model.name
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        samples: model.samples
                        points: model.points
                        xMin: root.vm.zoomStart
                        xMax: root.vm.zoomEnd
                        yLabel: model.unit ? model.unit : model.name.split(".").pop()
                        onZoomRequested: root.vm.zoomTo(from, to)
                        onResetRequested: root.vm.resetZoom()
                    }
                }
            }
            EmptyState {
                anchors.centerIn: parent
                visible: root.matches === 0
                iconName: "chart"
                title: "Not logged any more"
                body: root.fieldName + " was removed from the data logger. Add it again to see its graph here."
            }
        }
    }
}
