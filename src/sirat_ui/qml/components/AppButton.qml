import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

// variants: primary (one per view), secondary (default), ghost, danger, run (starts something: Run, Start, Execute)
Button {
    id: control
    property string variant: "secondary"
    property string iconName: ""
    property bool small: false
    property bool busy: false
    property string tip: ""

    readonly property color fg: variant === "primary" ? Theme.accentText
                              : variant === "run" ? Theme.runText
                              : variant === "danger" ? Theme.dangerFg : Theme.textPrimary

    hoverEnabled: true
    implicitHeight: small ? 24 : 28
    leftPadding: small ? 8 : 10
    rightPadding: small ? 8 : 10
    topPadding: 0
    bottomPadding: 0
    font.family: Theme.fontUi
    font.pixelSize: small ? Theme.fontXs : Theme.fontSm
    font.weight: Font.DemiBold
    opacity: enabled ? 1 : 0.45
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.description: tip
    ToolTip.visible: hovered && tip !== ""
    ToolTip.text: tip
    ToolTip.delay: 500

    contentItem: Row {
        spacing: 6
        Icon {
            visible: control.iconName !== "" || control.busy
            name: control.busy ? "sync" : control.iconName
            size: control.small ? 11 : 13
            color: control.fg
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: control.text
            font: control.font
            color: control.fg
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        radius: Theme.radiusSm
        color: control.variant === "primary" ? (control.hovered ? Theme.accentHover : Theme.accent)
             : control.variant === "run" ? (control.hovered ? Theme.runBgHover : Theme.runBg)
             : control.variant === "ghost" ? (control.hovered ? Theme.select : "transparent")
             : (control.hovered ? Theme.surface2 : Theme.surface)
        border.width: control.variant === "ghost" ? 0 : 1
        border.color: control.variant === "primary" ? Theme.accent
                    : control.variant === "run" ? Theme.runBg
                    : control.variant === "danger" ? Theme.dangerBg : Theme.borderStrong
    }

    // keyboard focus ring: only when focus came from the keyboard, never on mouse clicks
    Rectangle {
        z: 10
        anchors.fill: parent
        anchors.margins: -3
        radius: Theme.radiusSm + 3
        color: "transparent"
        border.width: 2
        border.color: Theme.focusRing
        visible: control.visualFocus
    }
}
