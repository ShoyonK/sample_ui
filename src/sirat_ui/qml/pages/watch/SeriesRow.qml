import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One logged field: name, latest value, and its plot (req 17: one plot per field, min 150 px).
Column {
    id: row
    property real xMin: -1
    property real xMax: -1
    signal removeRequested()
    signal zoomRequested(real from, real to)
    signal resetRequested()
    readonly property bool poppedOut: app.windows.openKeys.indexOf("graph:" + model.name) >= 0

    objectName: "series_" + model.name
    width: ListView.view ? ListView.view.width : 420
    spacing: 4

    RowLayout {
        width: parent.width
        Text {
            text: model.name + (model.unit ? " · " + model.unit : "")
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: model.lastText
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.infoFg
        }
        IconButton {
            objectName: "seriesPopOut_" + model.name
            iconName: "export"
            iconSize: 11
            implicitWidth: 20
            implicitHeight: 20
            tip: row.poppedOut ? "Show this graph's window" : "Open this graph in its own window"
            onClicked: app.windows.open("graph", model.name)
        }
        IconButton {
            objectName: "seriesRemove_" + model.name
            iconName: "close"
            iconSize: 11
            implicitWidth: 20
            implicitHeight: 20
            tip: "Stop logging this field"
            onClicked: row.removeRequested()
        }
    }
    PoppedOutPlaceholder {
        objectName: "graphPlaceholder_" + model.name
        visible: row.poppedOut
        compact: true
        width: parent.width
        onShowRequested: app.windows.show("graph:" + model.name)
        onDockRequested: app.windows.close("graph:" + model.name)
    }
    TimePlot {
        objectName: "plot_" + model.name
        visible: !row.poppedOut
        width: parent.width
        height: 170
        samples: model.samples
        points: model.points
        xMin: row.xMin
        xMax: row.xMax
        yLabel: model.unit ? model.unit : model.name.split(".").pop()
        onZoomRequested: row.zoomRequested(from, to)
        onResetRequested: row.resetRequested()
    }
}
