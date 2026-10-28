import QtQuick 2.15
import "../theme"
import "../components"

// Non-blocking notices, newest at the bottom; they dismiss themselves (DialogsViewModel.TOAST_MS).
Column {
    spacing: 8
    width: 380

    Repeater {
        model: app.dialogs.toasts
        delegate: Rectangle {
            objectName: "toast"
            width: 380
            height: Math.max(40, label.implicitHeight + 20)
            radius: Theme.radius
            color: Theme.surface
            border.color: model.level === "error" ? Theme.dangerFg : Theme.border

            Rectangle {
                width: 3
                height: parent.height - 16
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                radius: 2
                color: model.level === "error" ? Theme.dangerFg : model.level === "success" ? Theme.okFg : Theme.infoFg
            }
            Text {
                id: label
                anchors.left: parent.left
                anchors.right: closer.left
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                text: model.text
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontSm
                color: Theme.textPrimary
            }
            IconButton {
                id: closer
                tip: "Dismiss"
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                iconName: "close"
                iconSize: 10
                onClicked: app.dialogs.dismissToast(model.toastId)
            }
        }
    }
}
