import QtQuick 2.15

AppShellForm {
    objectName: "appShell"
    pageHost.currentPage: app.currentPage
    dockCollapsed: app.dock.collapsed
}
