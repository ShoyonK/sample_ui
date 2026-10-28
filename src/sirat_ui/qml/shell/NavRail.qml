import QtQuick 2.15

NavRailForm {
    function popped(key) { return app.windows.openKeys.indexOf("page:" + key) >= 0 }

    // Every page except settings goes in the column; settings is pinned to the bottom.
    pagesRepeater.model: app.pages.filter(function (p) { return p.key !== "settings" })
    pagesRepeater.delegate: NavButton {
        pageKey: modelData.key
        iconName: modelData.icon
        tip: modelData.title + (modelData.ready ? "" : " (planned)")
        ready: modelData.ready
        current: app.currentPage === modelData.key
        poppedOut: popped(modelData.key)
        // A popped-out page: the main window shows its placeholder and its window comes to the front.
        onClicked: { app.navigate(modelData.key); app.windows.show("page:" + modelData.key) }
        onPopOutRequested: app.windows.open("page", modelData.key)
        onShowWindowRequested: app.windows.show("page:" + modelData.key)
        onDockRequested: app.windows.close("page:" + modelData.key)
    }
    settingsButton.current: app.currentPage === "settings"
    settingsButton.tip: "Settings"
    settingsButton.poppedOut: popped("settings")
    settingsButton.onClicked: { app.navigate("settings"); app.windows.show("page:settings") }
    settingsButton.onPopOutRequested: app.windows.open("page", "settings")
    settingsButton.onShowWindowRequested: app.windows.show("page:settings")
    settingsButton.onDockRequested: app.windows.close("page:settings")
}
