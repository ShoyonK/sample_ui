import QtQuick 2.15
import "../../components"

// Honest placeholder for features scheduled in later phases of docs/FRONTEND_PLAN.md.
Card {
    property string title: ""
    property string body: ""
    property string iconName: "info"

    EmptyState {
        anchors.centerIn: parent
        iconName: parent.iconName
        title: parent.title
        body: parent.body
    }
}
