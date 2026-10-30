import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Req 20 Python Console: output, a multi-line input with history, Execute, Help, Restart session.
Card {
    id: root
    width: 1200
    height: 700

    property alias header: header
    property alias helpButton: helpButton
    property alias restartButton: restartButton
    property alias output: output
    property alias input: input
    property alias executeButton: executeButton

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        CardHeader {
            id: header
            title: "Python console"
            Layout.fillWidth: true
            AppButton { id: helpButton; objectName: "consoleHelpButton"; text: "Help"; iconName: "info"; small: true }
            AppButton { id: restartButton; objectName: "consoleRestartButton"; text: "Restart session"; iconName: "refresh"; small: true; tip: "Close the session and start with a clean namespace" }
        }
        OutputView {
            id: output
            prefix: "console"
            title: "Output"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.s3
            Layout.bottomMargin: Theme.s2
        }
        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.leftMargin: Theme.s3
            Layout.rightMargin: Theme.s3
            Layout.bottomMargin: Theme.s3
            ConsoleInput { id: input; objectName: "consoleInput"; Layout.fillWidth: true }
            AppButton { id: executeButton; objectName: "consoleExecuteButton"; text: "Execute"; iconName: "play"; variant: "run"; Layout.alignment: Qt.AlignBottom; Layout.bottomMargin: 4 }
        }
    }
}
