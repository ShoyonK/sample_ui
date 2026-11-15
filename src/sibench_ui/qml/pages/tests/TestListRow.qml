import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"

// One test in the selection panel; checked tests run.
Rectangle {
    id: row
    signal toggled()

    objectName: "testRow_" + model.id
    width: ListView.view ? ListView.view.width : 320
    height: 40
    color: hover.hovered ? Theme.surface2 : "transparent"
    HoverHandler { id: hover }
    TapHandler { enabled: row.enabled; onTapped: row.toggled() }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        spacing: Theme.s2

        AppCheckBox {
            objectName: "testCheck_" + model.id
            accessibleName: "Run " + model.name
            checked: model.checked
            nextCheckState: function() { return checkState }   // the ViewModel decides; the box follows it
            onClicked: row.toggled()
        }
        Text {
            text: model.name
            font.pixelSize: Theme.fontMd
            color: Theme.textPrimary
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.border
    }
}
