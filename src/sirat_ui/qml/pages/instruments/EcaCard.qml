import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../components"

EcaCardForm {
    readonly property var vm: app.eca

    status.text: vm.instrumentText
    status.found: vm.instrumentFound
    status.connected: vm.instrumentConnected
    status.onConnectRequested: vm.connectInstrument()
    channelRepeater.model: vm.channels
    channelRepeater.delegate: AppCheckBox {
        objectName: "ecaChannel_" + model.name
        text: model.name
        checked: model.checked
        enabled: !vm.busy
        onClicked: vm.toggleChannel(index)
    }
    triggerCombo.model: vm.triggers
    triggerCombo.currentIndex: vm.triggerIndex
    triggerCombo.onActivated: vm.setTrigger(index)
    edgeControl.currentIndex: vm.edgeIndex
    edgeControl.enabled: vm.triggerIndex > 0
    edgeControl.onActivated: vm.setEdge(index)
    rateField.text: vm.rate
    rateField.onTextEdited: vm.setField("rate", rateField.text)
    rateField.invalid: !!vm.errors.rate
    durationField.text: vm.duration
    durationField.onTextEdited: vm.setField("duration", durationField.text)
    durationField.invalid: !!vm.errors.duration
    pretriggerField.text: vm.pretrigger
    pretriggerField.onTextEdited: vm.setField("pretrigger", pretriggerField.text)
    pretriggerField.invalid: !!vm.errors.pretrigger
    samplesLabel.text: vm.samplesText
    errorLabel.text: vm.errorText
    captureButton.enabled: vm.canCapture
    captureButton.busy: vm.busy
    captureButton.visible: !vm.capturing
    stopButton.visible: vm.capturing
    stopButton.onClicked: vm.abort()
    captureButton.onClicked: vm.capture()
    progressLabel.text: vm.progressText

    plotsEmpty.visible: !vm.hasCapture
    plotRepeater.model: vm.plots
    plotRepeater.delegate: ChannelPlot {
        name: model.name
        xs: model.xs
        ys: model.ys
        tone: model.tone
        xMin: vm.xMin
        xMax: vm.xMax
        markers: vm.markers
        Layout.fillWidth: true
        onZoomRequested: vm.zoom(from, to)
        onResetRequested: vm.resetZoom()
    }
    analysis.visible: vm.hasCapture
    markerAField.text: vm.markerA
    markerAField.onTextEdited: vm.setField("markerA", markerAField.text)
    markerAField.invalid: !!vm.errors.markerA
    markerBField.text: vm.markerB
    markerBField.onTextEdited: vm.setField("markerB", markerBField.text)
    markerBField.invalid: !!vm.errors.markerB
    markerLabel.text: vm.markerText
    resetZoomButton.enabled: vm.xMin >= 0
    resetZoomButton.onClicked: vm.resetZoom()
    saveButton.onClicked: vm.saveCsv()
    measureList.model: vm.measurements
    measureList.delegate: MeasurementRow {}
}
