import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 13 Edit dialog: values of register/field operations are editable; others are shown as info.
ModalDialog {
    id: dialog
    objectName: "actionEditDialog"
    readonly property var vm: app.actionEditor

    visible: vm.editOpen
    dialogWidth: 760

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: dialog.vm.editTitle
            message: "Change register and field values, then save. Values are hex unless prefixed with 0b or 0o."
            iconName: "edit"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        ListView {
            id: rows
            objectName: "actionEditRows"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(360, Math.max(80, count * 46))
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            clip: true
            model: dialog.vm.editRows
            ScrollBar.vertical: AppScrollBar {}
            delegate: Rectangle {
                width: ListView.view ? ListView.view.width : 700
                height: 46
                color: "transparent"
                RowLayout {
                    anchors.fill: parent
                    spacing: Theme.s2
                    Text {
                        text: (model.index + 1) + "."
                        font.family: Theme.fontMono
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                        Layout.preferredWidth: 24
                    }
                    Chip {
                        text: model.kind.replace(/_/g, " ")
                        accent: model.editable ? "transparent" : Theme.kindColor(model.kind)
                        tone: "ok"
                        Layout.preferredWidth: 130
                    }
                    Column {
                        Layout.fillWidth: true
                        Text {
                            text: model.description
                            width: parent.width
                            elide: Text.ElideRight
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontSm
                            color: Theme.textPrimary
                        }
                        Text {
                            visible: model.info !== ""
                            text: model.info
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }
                    }
                    AppTextField {
                        visible: model.editable
                        objectName: "editValue_" + model.index
                        mono: true
                        text: model.valueText
                        Layout.preferredWidth: 150
                        onTextEdited: dialog.vm.setEditValue(model.index, text)
                    }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            Item { Layout.fillWidth: true }
            AppButton { objectName: "actionEditCancelButton"; text: "Cancel"; onClicked: dialog.vm.cancelEdit() }
            AppButton { objectName: "actionEditSaveButton"; text: "Save"; variant: "primary"; onClicked: dialog.vm.saveEdit() }
        }
    }
}
