import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../shell"

// Advanced: three station-side tools behind one tab row. The console and custom functions share a session
// (req 15, 20); the memory viewer (req 19) stands alone. The DUT control explorer (req 22) is its own page.
ColumnLayout {
    id: root
    width: 1500
    height: 760
    spacing: 10

    property alias tabs: tabs
    property alias stack: stack

    SegmentedControl {
        id: tabs
        objectName: "advancedTabs"
        model: ["Console", "Custom functions", "Memory"]
    }

    StackLayout {
        id: stack
        Layout.fillWidth: true
        Layout.fillHeight: true
        ToolSlot { toolKey: "pyConsole" }
        ToolSlot { toolKey: "customFunctions" }
        ToolSlot { toolKey: "memory" }
    }
}
