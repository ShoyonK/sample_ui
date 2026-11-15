import QtQuick 2.15
import "../dock"

// Larger view of the same actions as the dock panel, with reorder and delete (req 13).
ActionsPanel {
    showManagement: true
    header.meta: "check actions to include in Run checked and generated code · select a row to run or move it"
}
