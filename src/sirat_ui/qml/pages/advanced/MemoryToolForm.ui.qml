import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 19 Memory Viewer: address, size and format, Read; the hex dump (bytes with ASCII, words, dwords);
// a byte/word/dword write that is always confirmed.
Card {
    id: root
    width: 1200
    height: 700

    property alias addressField: addressField
    property alias sizeField: sizeField
    property alias formatControl: formatControl
    property alias readButton: readButton
    property alias copyButton: copyButton
    property alias readError: readError
    property alias headerLabel: headerLabel
    property alias dumpList: dumpList
    property alias emptyState: emptyState
    property alias writeAddressField: writeAddressField
    property alias writeValueField: writeValueField
    property alias writeSizeControl: writeSizeControl
    property alias writeButton: writeButton
    property alias writeError: writeError

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader {
            title: "Memory"
            meta: "last address saved to ~/.sirat/memory_viewer.json"
            Layout.fillWidth: true
            AppButton { id: copyButton; objectName: "memoryCopyButton"; text: "Copy dump"; iconName: "copy"; small: true }
        }

        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.margins: Theme.s3
            Layout.bottomMargin: Theme.s2
            Text { text: "Address"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            AppTextField { id: addressField; objectName: "memoryAddressField"; mono: true; placeholderText: "0x20000000"; Layout.preferredWidth: 150 }
            Text { text: "Size"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.leftMargin: Theme.s2 }
            AppTextField { id: sizeField; objectName: "memorySizeField"; mono: true; selectOnFocus: true; placeholderText: "256"; Layout.preferredWidth: 80 }
            Text { text: "bytes"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            SegmentedControl { id: formatControl; objectName: "memoryFormatControl"; Layout.leftMargin: Theme.s3 }
            AppButton { id: readButton; objectName: "memoryReadButton"; text: "Read"; iconName: "download"; variant: "primary"; Layout.leftMargin: Theme.s2 }
            Text {
                id: readError
                objectName: "memoryReadError"
                font.pixelSize: Theme.fontXs
                color: Theme.dangerFg
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.leftMargin: Theme.s2
            }
        }

        Text {
            id: headerLabel
            objectName: "memoryHeader"
            font.family: Theme.fontMono
            font.pixelSize: Theme.fontXs
            color: Theme.textMuted
            Layout.leftMargin: Theme.s3
            Layout.bottomMargin: 4
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: Theme.s3
            Layout.rightMargin: Theme.s3
            radius: Theme.radius
            color: Theme.surface2
            border.color: Theme.border
            ListView {
                id: dumpList
                objectName: "memoryDump"
                anchors.fill: parent
                anchors.topMargin: 6
                anchors.bottomMargin: 6
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: AppScrollBar {}
                delegate: MemoryRow {}
            }
            EmptyState {
                id: emptyState
                anchors.centerIn: parent
                width: parent.width - 80
                iconName: "cpu"
                title: "No memory read yet"
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border; Layout.topMargin: Theme.s3 }
        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.margins: Theme.s3
            Text { text: "Write"; font.pixelSize: Theme.fontSm; font.weight: Font.DemiBold; color: Theme.textPrimary; Layout.rightMargin: Theme.s2 }
            Text { text: "Address"; font.pixelSize: Theme.fontSm; color: Theme.textMuted }
            AppTextField { id: writeAddressField; objectName: "memoryWriteAddressField"; mono: true; placeholderText: "0x20000000"; Layout.preferredWidth: 150 }
            Text { text: "Value"; font.pixelSize: Theme.fontSm; color: Theme.textMuted; Layout.leftMargin: Theme.s2 }
            AppTextField { id: writeValueField; objectName: "memoryWriteValueField"; mono: true; placeholderText: "0x00000000"; Layout.preferredWidth: 150 }
            SegmentedControl { id: writeSizeControl; objectName: "memoryWriteSizeControl"; Layout.leftMargin: Theme.s3 }
            AppButton { id: writeButton; objectName: "memoryWriteButton"; text: "Write…"; iconName: "upload"; variant: "danger"; Layout.leftMargin: Theme.s2 }
            Text {
                id: writeError
                objectName: "memoryWriteError"
                font.pixelSize: Theme.fontXs
                color: Theme.dangerFg
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.leftMargin: Theme.s2
            }
        }
    }
}
