import QtQuick 2.15

WatchPageForm {
    readonly property bool watchPopped: app.windows.openKeys.indexOf("watchList") >= 0
    readonly property bool loggerPopped: app.windows.openKeys.indexOf("logger") >= 0

    watchPanel.visible: !watchPopped
    watchPlaceholder.visible: watchPopped
    watchPlaceholder.onShowRequested: app.windows.show("watchList")
    watchPlaceholder.onDockRequested: app.windows.close("watchList")
    logger.visible: !loggerPopped
    loggerPlaceholder.visible: loggerPopped
    loggerPlaceholder.onShowRequested: app.windows.show("logger")
    loggerPlaceholder.onDockRequested: app.windows.close("logger")
}
