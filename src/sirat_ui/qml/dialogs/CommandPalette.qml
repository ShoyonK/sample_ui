import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

// Ctrl+K: type to find a register (or field), page, action, sequence or command. Up/Down, Enter, Esc.
Popup {
    id: palette
    objectName: "commandPalette"
    readonly property var vm: app.palette

    parent: Overlay.overlay
    visible: vm.isOpen
    modal: true
    dim: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: Math.min(680, parent ? parent.width - 80 : 680)
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: 70
    padding: 0
    onOpened: {
        field.text = ""
        field.forceActiveFocus()
    }
    onClosed: if (vm.isOpen) vm.close()

    background: Rectangle {
        radius: 12
        color: Theme.surface
        border.color: Theme.border
    }
    Overlay.modal: Rectangle { color: Theme.overlay }

    contentItem: ColumnLayout {
        spacing: 0
        AppTextField {
            id: field
            objectName: "paletteField"
            Layout.fillWidth: true
            Layout.margins: 12
            implicitHeight: 36
            leadingIcon: "search"
            placeholderText: "Jump to a register, field, page, action or sequence"
            font.pixelSize: Theme.fontMd
            onTextEdited: palette.vm.setQuery(text)
            Keys.onDownPressed: palette.vm.move(1)
            Keys.onUpPressed: palette.vm.move(-1)
            Keys.onReturnPressed: palette.vm.activateCurrent()
            Keys.onEnterPressed: palette.vm.activateCurrent()
            Keys.onEscapePressed: palette.vm.close()
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }
        ListView {
            id: results
            objectName: "paletteResults"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(420, Math.max(44, count * 44))
            clip: true
            model: palette.vm.results
            currentIndex: palette.vm.currentIndex
            onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
            ScrollBar.vertical: AppScrollBar {}
            delegate: Rectangle {
                objectName: "paletteItem_" + model.key
                width: ListView.view ? ListView.view.width : 600
                height: 44
                color: model.current ? Theme.select : (hover.hovered ? Theme.surface2 : "transparent")
                HoverHandler { id: hover }
                TapHandler { onTapped: palette.vm.activate(index) }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 10
                    Chip {
                        text: model.kind
                        tone: model.kind === "register" ? "ok" : model.kind === "page" ? "info"
                            : model.kind === "action" ? "warn" : model.kind === "sequence" ? "split" : "mute"
                        Layout.preferredWidth: 72
                    }
                    Column {
                        Layout.fillWidth: true
                        Text {
                            text: model.title
                            width: parent.width
                            elide: Text.ElideRight
                            font.family: model.kind === "register" || model.kind === "action" || model.kind === "sequence"
                                         ? Theme.fontMono : Theme.fontUi
                            font.pixelSize: Theme.fontMd
                            color: Theme.textPrimary
                        }
                        Text {
                            text: model.subtitle
                            width: parent.width
                            elide: Text.ElideRight
                            font.pixelSize: Theme.fontXs
                            color: Theme.textMuted
                        }
                    }
                    Rectangle {
                        objectName: "paletteShortcut_" + model.key
                        visible: model.shortcut !== ""
                        implicitWidth: keyText.implicitWidth + 12
                        implicitHeight: 20
                        radius: Theme.radiusSm
                        color: Theme.surface2
                        border.color: Theme.borderStrong
                        Text {
                            id: keyText
                            anchors.centerIn: parent
                            text: model.shortcut
                            font.family: Theme.fontMono
                            font.pixelSize: Theme.fontXs
                            color: Theme.textPrimary
                        }
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: results.count === 0
                text: "No matches"
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
            }
        }
        Text {
            Layout.margins: 10
            Layout.leftMargin: 16
            text: "↑↓ to move · Enter to open · Esc to close"
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
        }
    }
}
