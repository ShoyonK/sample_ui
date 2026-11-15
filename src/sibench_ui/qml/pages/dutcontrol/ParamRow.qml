import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One parameter of the selected method: a True/False switch for bool, a text field for everything else.
RowLayout {
    id: row
    signal edited(string name, string value)
    // copied out because the SegmentedControl's own `model` would shadow the delegate's
    readonly property string paramName: model.name
    readonly property string paramValue: model.value
    readonly property bool isBool: model.isBool

    spacing: Theme.s3

    Text {
        text: row.paramName + (model.required ? " *" : "")
        font.family: Theme.fontMono
        font.pixelSize: Theme.fontSm
        color: Theme.textPrimary
        elide: Text.ElideRight
        Layout.preferredWidth: 140
    }
    SegmentedControl {
        visible: row.isBool
        objectName: "param_" + row.paramName + "_bool"
        small: true
        model: ["False", "True"]
        currentIndex: row.boolIndex(row.paramValue)
        onActivated: row.edited(row.paramName, index === 1 ? "True" : "False")
    }
    AppTextField {
        visible: !row.isBool
        objectName: "param_" + row.paramName
        mono: true
        text: row.paramValue
        placeholderText: model.placeholder
        Layout.preferredWidth: 240
        onTextEdited: row.edited(row.paramName, text)
    }
    Text {
        text: model.annotation
        font.family: Theme.fontMono
        font.pixelSize: Theme.fontXs
        color: Theme.textMuted
        Layout.fillWidth: true
    }

    function boolIndex(v) {
        var s = String(v).toLowerCase()
        return s === "true" ? 1 : s === "false" ? 0 : -1
    }
}
