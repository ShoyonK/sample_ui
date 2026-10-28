import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

Card {
    id: root
    width: 360
    height: 760

    property alias searchField: searchField
    property alias list: list
    property alias collapseButton: collapseButton
    property alias countLabel: countLabel

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            implicitHeight: 48
            AppTextField {
                id: searchField
                objectName: "treeSearchField"
                anchors.fill: parent
                anchors.margins: 10
                leadingIcon: "search"
                placeholderText: "Filter peripherals, registers, fields"
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.s3
            Layout.rightMargin: Theme.s3
            implicitHeight: 26
            Text { text: "Name"; color: Theme.textMuted; font.pixelSize: Theme.fontXs; Layout.fillWidth: true }
            Text { text: "Address"; color: Theme.textMuted; font.pixelSize: Theme.fontXs; Layout.preferredWidth: 84 }
            Text {
                text: "Value"
                color: Theme.textMuted
                font.pixelSize: Theme.fontXs
                horizontalAlignment: Text.AlignRight
                Layout.preferredWidth: 80
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

        ListView {
            id: list
            objectName: "treeList"
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: AppScrollBar {}
            delegate: TreeRow {}
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.s2
            AppButton {
                id: collapseButton
                objectName: "collapseAllButton"
                text: "Collapse all"
                iconName: "fold"
                variant: "ghost"
                small: true
            }
            Item { Layout.fillWidth: true }
            Text {
                id: countLabel
                text: "12 peripherals"
                color: Theme.textMuted
                font.pixelSize: Theme.fontXs
            }
        }
    }
}
