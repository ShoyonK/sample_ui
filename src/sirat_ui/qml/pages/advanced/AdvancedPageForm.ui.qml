import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// Advanced: four station-side Python tools behind one tab row. The console and custom functions share a
// session (req 15, 20); the DUT control explorer (req 22) and the memory viewer (req 19) stand alone.
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
        model: ["Console", "Custom functions", "DUT control", "Memory"]
    }

    StackLayout {
        id: stack
        Layout.fillWidth: true
        Layout.fillHeight: true
        ConsoleTool {}
        FunctionsTool {}
        DutControlTool {}
        MemoryTool {}
    }
}
