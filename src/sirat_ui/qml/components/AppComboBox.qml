import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

ComboBox {
    id: control
    implicitHeight: 24
    font.family: Theme.fontUi
    font.pixelSize: Theme.fontXs

    contentItem: Text {
        leftPadding: 8
        rightPadding: 24
        text: control.displayText
        font: control.font
        color: Theme.textPrimary
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Icon {
        x: control.width - width - 8
        y: (control.height - height) / 2
        name: "chevronDown"
        size: 10
    }
    background: Rectangle {
        radius: Theme.radiusSm
        color: Theme.surface
        border.color: Theme.borderStrong
    }
    popup.background: Rectangle {
        radius: Theme.radiusSm
        color: Theme.surface
        border.color: Theme.border
    }
    delegate: ItemDelegate {
        width: control.width
        height: 26
        contentItem: Text {
            text: modelData
            font: control.font
            color: Theme.textPrimary
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle { color: highlighted ? Theme.select : Theme.surface }
        highlighted: control.highlightedIndex === index
    }
}
