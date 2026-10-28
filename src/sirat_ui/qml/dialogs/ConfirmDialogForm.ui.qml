import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Content of the confirmation dialog (req 7: critical write confirmation).
ColumnLayout {
    id: root
    width: 480
    spacing: 14

    property alias header: header
    property alias details: details
    property alias warningBox: warningBox
    property alias warningLabel: warningLabel
    property alias dontShowBox: dontShowBox
    property alias cancelButton: cancelButton
    property alias confirmButton: confirmButton

    DialogHeader {
        id: header
        title: "Confirm write to critical register"
        message: "CMU is a critical peripheral. Check the value before writing."
        Layout.fillWidth: true
        Layout.topMargin: 18
        Layout.leftMargin: 20
        Layout.rightMargin: 20
    }
    KeyValueGrid {
        id: details
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
    }
    Rectangle {
        id: warningBox
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
        implicitHeight: warningLabel.implicitHeight + 20
        radius: Theme.radius
        color: Theme.dangerBg
        Text {
            id: warningLabel
            anchors.fill: parent
            anchors.margins: 10
            text: "Writing an incorrect value can lock up the device or drop debug access."
            wrapMode: Text.WordWrap
            font.pixelSize: Theme.fontSm
            color: Theme.dangerFg
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
        Layout.bottomMargin: 18
        spacing: Theme.s2
        AppCheckBox { id: dontShowBox; objectName: "dontShowAgainBox"; text: "Don't show this again" }
        Item { Layout.fillWidth: true }
        AppButton { id: cancelButton; objectName: "confirmCancelButton"; text: "Cancel" }
        AppButton { id: confirmButton; objectName: "confirmAcceptButton"; text: "Write"; variant: "primary" }
    }
}
