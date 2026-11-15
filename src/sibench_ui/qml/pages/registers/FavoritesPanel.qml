import QtQuick 2.15

FavoritesPanelForm {
    readonly property var vm: app.favorites

    header.meta: vm.model.count + ""
    list.model: vm.model
    list.delegate: FavoriteRow {
        onActivated: vm.activate(index)
        onRemoveRequested: vm.remove(index)
    }
}
