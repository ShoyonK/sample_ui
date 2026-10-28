import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One captured channel: its name and a time plot sharing the X range and markers with the other channels.
ColumnLayout {
    id: root
    property string name: ""
    property var xs: []
    property var ys: []
    property string tone: "info"
    property real xMin: -1
    property real xMax: -1
    property var markers: []
    signal zoomRequested(real from, real to)
    signal resetRequested()

    objectName: "ecaPlot_" + name
    spacing: 2
    Layout.fillWidth: true
    Text { text: root.name; font.family: Theme.fontMono; font.pixelSize: Theme.fontXs; font.weight: Font.DemiBold; color: Theme.toneFg(root.tone) }
    TimePlot {
        samples: root.xs
        points: root.ys
        xMin: root.xMin
        xMax: root.xMax
        markers: root.markers
        minXStep: 0
        xLabel: "Time (ms)"
        yLabel: "mV"
        lineColor: Theme.toneFg(root.tone)
        lineWidth: 1.5
        Layout.fillWidth: true
        Layout.preferredHeight: 120
        onZoomRequested: root.zoomRequested(from, to)
        onResetRequested: root.resetRequested()
    }
}
