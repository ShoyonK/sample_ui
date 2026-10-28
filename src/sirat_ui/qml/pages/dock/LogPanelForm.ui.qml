import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 35 log view: level checkboxes, search with next/previous, save, clear, pop-out.
Card {
    id: root
    width: 500
    height: 230

    property alias header: header
    property alias levelControl: levelControl
    property alias searchField: searchField
    property alias matchLabel: matchLabel
    property alias previousButton: previousButton
    property alias nextButton: nextButton
    property alias saveButton: saveButton
    property alias clearButton: clearButton
    property alias popOutButton: popOutButton
    property alias list: list

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        CardHeader {
            id: header
            title: "Log"
            Layout.fillWidth: true
            IconButton { id: saveButton; objectName: "logSaveButton"; iconName: "save"; tip: "Save log…" }
            IconButton { id: clearButton; objectName: "logClearButton"; iconName: "erase"; tip: "Clear log" }
            IconButton { id: popOutButton; objectName: "logPopOutButton"; iconName: "export"; tip: "Open in its own window" }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.s2
            Layout.rightMargin: Theme.s2
            Layout.topMargin: 6
            spacing: 6
            SegmentedControl {
                id: levelControl
                objectName: "logLevels"
                model: ["Debug", "Info", "Warning", "Error"]
                multi: true
                small: true
                checkedStates: [true, true, true, true]
            }
            AppTextField {
                id: searchField
                objectName: "logSearchField"
                leadingIcon: "search"
                implicitHeight: 24
                placeholderText: "Search"
                Layout.fillWidth: true
            }
            Text {
                id: matchLabel
                text: ""
                visible: text !== ""
                font.pixelSize: Theme.fontXs
                color: Theme.textMuted
            }
            IconButton { id: previousButton; objectName: "logPreviousMatch"; iconName: "up"; tip: "Previous match"; implicitWidth: 22; implicitHeight: 22 }
            IconButton { id: nextButton; objectName: "logNextMatch"; iconName: "down"; tip: "Next match"; implicitWidth: 22; implicitHeight: 22 }
        }

        ListView {
            id: list
            objectName: "logList"
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.s2
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: AppScrollBar {}
            delegate: Rectangle {
                width: ListView.view ? ListView.view.width : 400
                height: line.implicitHeight + 2
                color: model.current ? Theme.changed : model.match ? Theme.noteBg : "transparent"
                Text {
                    id: line
                    width: parent.width
                    text: model.text
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontXs
                    color: Theme.logColor(model.level)
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                }
            }
        }
    }
}
