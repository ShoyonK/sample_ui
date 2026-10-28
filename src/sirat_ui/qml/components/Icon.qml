import QtQuick 2.15
import "../theme"

// Icons from the Segoe MDL2 Assets font that ships with Windows 10/11, so no image assets are needed.
Text {
    id: root
    property string name: ""
    property int size: 16

    readonly property var glyphs: ({
        cpu: "", pulse: "", bolt: "", list: "", compare: "",
        antenna: "", wave: "", terminal: "", flask: "", settings: "",
        search: "", star: "", starFilled: "", eye: "", chart: "",
        chevronRight: "", chevronDown: "", box: "", play: "", pause: "",
        stop: "", refresh: "", sync: "", copy: "", delete: "",
        code: "", save: "", download: "", upload: "", add: "",
        close: "", edit: "", warning: "", check: "", plug: "",
        moon: "", sun: "", up: "", down: "", info: "",
        error: "", fold: "", next: "", export: "", erase: "", textSize: ""
    })

    text: glyphs[name] || ""
    font.family: Theme.fontIcons
    font.pixelSize: Theme.px(size)  // icons follow Theme.fontScale too
    color: Theme.textMuted
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
}
