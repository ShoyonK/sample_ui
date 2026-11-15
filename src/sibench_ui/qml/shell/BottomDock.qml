import QtQuick 2.15

BottomDockForm {
    collapsed: app.dock.collapsed
    showActions: app.currentPage !== "actions"
}
