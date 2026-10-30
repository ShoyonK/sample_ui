import QtQuick 2.15
import "../components"
import "../dialogs"

// Shows whatever InteractionService requests are pending, plus the disconnect dialog and connect sheet.
Item {
    OverlayTracker { isHome: true }
    ConfirmDialog { }
    AlertDialog { }
    PromptDialog { }
    ActionViewDialog { }
    ActionEditDialog { }
    FormulaDialog { }
    CodeDialog { }
    ReadAllDialog { }
    CommandPalette { }
    SessionBrowserDialog { }
    DumpPickerDialog { }
    DumpProgressDialog { }
    WifiResultDialog { }
    DisconnectDialog { }
    ConnectSheet { }
    ToastStack {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 20
        anchors.bottomMargin: 40
    }
}
