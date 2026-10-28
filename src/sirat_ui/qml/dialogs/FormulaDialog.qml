import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 11 Field Formula dialog: formula + unit, examples, Test (x = 100), Save, Remove, Cancel.
ModalDialog {
    id: dialog
    objectName: "formulaDialog"
    readonly property var vm: app.formulaEditor

    visible: vm.isOpen
    dialogWidth: 600

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: "Define calculation formula"
            message: dialog.vm.fieldName
            iconName: "edit"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            implicitHeight: help.implicitHeight + 20
            radius: Theme.radius
            color: Theme.surface2
            border.color: Theme.border
            Column {
                id: help
                anchors.fill: parent
                anchors.margins: 10
                spacing: 4
                Text {
                    text: "Use x for the raw field value. Allowed: + - * / // % ** & | ^ << >>, abs, round, min, max, pow, pi, e. Click an example to use it."
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: Theme.fontXs
                    color: Theme.textMuted
                }
                Repeater {
                    model: dialog.vm.examples
                    delegate: Text {
                        objectName: "formulaExample_" + index
                        text: "<span style='font-family:Consolas'>" + modelData.formula + "</span>  " + modelData.unit
                              + "  <font color='" + Theme.textMuted + "'>· " + modelData.label + "</font>"
                        textFormat: Text.StyledText
                        font.pixelSize: Theme.fontSm
                        color: Theme.infoFg
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: dialog.vm.useExample(index)
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            spacing: Theme.s2
            ColumnLayout {
                spacing: 4
                Layout.fillWidth: true
                Text { text: "Formula"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                AppTextField {
                    id: exprField
                    objectName: "formulaExprField"
                    mono: true
                    Layout.fillWidth: true
                    placeholderText: "x * 40e6 / 2**19"
                    text: dialog.vm.expr
                    onTextEdited: dialog.vm.setExpr(text)
                    onAccepted: dialog.vm.test()
                }
            }
            ColumnLayout {
                spacing: 4
                Text { text: "Unit"; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                AppTextField {
                    objectName: "formulaUnitField"
                    Layout.preferredWidth: 120
                    placeholderText: "Hz"
                    text: dialog.vm.unit
                    onTextEdited: dialog.vm.setUnit(text)
                }
            }
            AppButton {
                objectName: "formulaTestButton"
                text: "Test"
                iconName: "play"
                Layout.alignment: Qt.AlignBottom
                onClicked: dialog.vm.test()
            }
        }

        Text {
            objectName: "formulaTestResult"
            visible: text !== ""
            text: dialog.vm.testText
            wrapMode: Text.WordWrap
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontSm
            color: dialog.vm.testOk ? Theme.okFg : Theme.dangerFg
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            spacing: Theme.s2
            AppButton {
                objectName: "formulaRemoveButton"
                visible: dialog.vm.hasExisting
                text: "Remove formula"
                iconName: "delete"
                variant: "danger"
                onClicked: dialog.vm.remove()
            }
            Item { Layout.fillWidth: true }
            AppButton { objectName: "formulaCancelButton"; text: "Cancel"; onClicked: dialog.vm.cancel() }
            AppButton { objectName: "formulaSaveButton"; text: "Save formula"; iconName: "save"; variant: "primary"; onClicked: dialog.vm.save() }
        }
    }
}
