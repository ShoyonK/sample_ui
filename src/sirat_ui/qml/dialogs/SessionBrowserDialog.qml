import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Req 34 Load Session: saved sessions with date and summary, a preview, Load or Delete.
ModalDialog {
    id: dialog
    objectName: "sessionBrowser"
    readonly property var vm: app.sessions

    visible: vm.browserOpen
    dialogWidth: 860

    contentItem: ColumnLayout {
        spacing: 12
        DialogHeader {
            title: "Load session"
            message: "Loading replaces your notes, formulas, actions, favorites and history with the session's."
            iconName: "download"
            tone: "info"
            Layout.fillWidth: true
            Layout.topMargin: 18
            Layout.leftMargin: 20
            Layout.rightMargin: 20
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            spacing: 12

            Rectangle {
                Layout.preferredWidth: 380
                Layout.preferredHeight: 360
                radius: Theme.radius
                color: Theme.surface
                border.color: Theme.border
                clip: true
                ListView {
                    id: list
                    objectName: "sessionList"
                    anchors.fill: parent
                    anchors.margins: 1
                    model: dialog.vm.model
                    ScrollBar.vertical: AppScrollBar {}
                    delegate: Rectangle {
                        objectName: "sessionRow_" + model.name
                        width: ListView.view ? ListView.view.width : 360
                        height: 54
                        color: model.selected ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
                        HoverHandler { id: hover }
                        TapHandler {
                            onTapped: dialog.vm.select(index)
                            onDoubleTapped: {
                                dialog.vm.select(index)
                                dialog.vm.loadSelected()
                            }
                        }
                        Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2
                            RowLayout {
                                width: parent.width
                                Text {
                                    text: model.name
                                    font.family: Theme.fontMono
                                    font.pixelSize: Theme.fontSm
                                    font.weight: Font.DemiBold
                                    color: Theme.textPrimary
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                Text { text: model.modified; font.pixelSize: Theme.fontXs; color: Theme.textMuted }
                            }
                            Text {
                                text: model.summary
                                width: parent.width
                                elide: Text.ElideRight
                                font.pixelSize: Theme.fontXs
                                color: Theme.textMuted
                            }
                        }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                    }
                    EmptyState {
                        anchors.centerIn: parent
                        visible: list.count === 0
                        iconName: "save"
                        title: "No saved sessions"
                        body: "Use Save session on the Settings page to save one."
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 360
                clip: true
                KeyValueGrid {
                    objectName: "sessionPreview"
                    width: parent.width
                    rows: dialog.vm.preview
                    monoValues: false
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.bottomMargin: 18
            spacing: Theme.s2
            AppButton {
                objectName: "sessionDeleteButton"
                text: "Delete"
                iconName: "delete"
                variant: "danger"
                enabled: dialog.vm.selectedName !== ""
                onClicked: dialog.vm.deleteSelected()
            }
            Item { Layout.fillWidth: true }
            AppButton { objectName: "sessionCloseButton"; text: "Close"; onClicked: dialog.vm.closeBrowser() }
            AppButton {
                objectName: "sessionLoadButton"
                text: "Load"
                iconName: "download"
                variant: "primary"
                enabled: dialog.vm.selectedName !== ""
                onClicked: dialog.vm.loadSelected()
            }
        }
    }
}
