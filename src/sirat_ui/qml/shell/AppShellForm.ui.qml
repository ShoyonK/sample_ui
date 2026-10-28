import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

// Window layout: top bar, nav rail, page area over the bottom dock, status bar.
Item {
    id: root
    width: 1600
    height: 950

    property alias topBar: topBar
    property alias navRail: navRail
    property alias pageHost: pageHost
    property alias bottomDock: bottomDock
    property alias statusBar: statusBar

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TopBar {
            id: topBar
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: 0
            Layout.fillWidth: true
            Layout.fillHeight: true

            NavRail {
                id: navRail
                Layout.fillHeight: true
            }

            SplitView {
                orientation: Qt.Vertical
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 10

                handle: Item {
                    implicitHeight: 10
                    Rectangle {
                        anchors.centerIn: parent
                        width: 36
                        height: 3
                        radius: 2
                        color: Theme.borderStrong
                    }
                }

                PageHost {
                    id: pageHost
                    SplitView.fillHeight: true
                    SplitView.minimumHeight: 320
                }

                BottomDock {
                    id: bottomDock
                    SplitView.preferredHeight: 230
                    SplitView.minimumHeight: 120
                }
            }
        }

        StatusBar {
            id: statusBar
            Layout.fillWidth: true
        }
    }
}
