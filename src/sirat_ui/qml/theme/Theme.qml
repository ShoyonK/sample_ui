pragma Singleton
import QtQuick 2.15

// Design tokens. Every color, size and font in the app comes from here, so dark mode is one flag.
QtObject {
    property bool dark: false

    // surfaces
    readonly property color canvas:       dark ? "#111214" : "#F6F6F4"
    readonly property color surface:      dark ? "#1A1B1E" : "#FFFFFF"
    readonly property color surface2:     dark ? "#1F2023" : "#FAFAF8"
    readonly property color select:       dark ? "#26272B" : "#F0F0EC"
    readonly property color border:       dark ? "#2A2C30" : "#E6E6E3"
    readonly property color borderStrong: dark ? "#3A3C41" : "#D6D6D2"

    // text
    readonly property color textPrimary: dark ? "#ECECEC" : "#1C1C1C"
    // muted text carries data too (addresses, headers), so it keeps 4.5:1: about 5.3:1 on surface in light,
    // 6.2:1 in dark
    readonly property color textMuted:   dark ? "#9A9A9A" : "#6B6B67"

    // primary action
    readonly property color accent:      dark ? "#FFFFFF" : "#111111"
    readonly property color accentHover: dark ? "#DCDCDC" : "#333333"
    readonly property color accentText:    dark ? "#111111" : "#FFFFFF"

    // semantic tints: background / foreground pairs
    readonly property color infoBg:   dark ? "#1C2540" : "#EEF3FF"
    readonly property color infoFg:   dark ? "#8EA6F5" : "#3B5BDB"
    readonly property color okBg:     dark ? "#16301F" : "#EAF7EE"
    readonly property color okFg:     dark ? "#6FCF8A" : "#2B8A3E"
    readonly property color warnBg:   dark ? "#3A2A12" : "#FFF4E5"
    readonly property color warnFg:   dark ? "#F2B262" : "#C76A00"
    readonly property color dangerBg: dark ? "#3A1A1A" : "#FDECEC"
    readonly property color dangerFg: dark ? "#F28B8B" : "#C92A2A"
    readonly property color splitBg:  dark ? "#272040" : "#F1EEFF"
    readonly property color splitFg:  dark ? "#B4A2F5" : "#6741D9"
    readonly property color focusRing: dark ? "#8EA6F5" : "#3B5BDB"   // keyboard focus, same hue as info
    readonly property color changed:  dark ? "#3D3814" : "#FFF6BF"   // changed-field highlight (req 5)

    // bit grid: set bits are a soft red tint with deep red digits, so the pattern reads without glare
    readonly property color bitOn:       dark ? "#4A2626" : "#FFD8D8"
    readonly property color bitOnBorder: dark ? "#7A3A3A" : "#F4A3A3"
    readonly property color bitOnText:   dark ? "#FFB4B4" : "#B42525"
    readonly property color bitHover:    dark ? "#2C1E1E" : "#FFF3F3"

    // checked checkboxes are solid ink, so "checked" never reads as an error or a set bit
    readonly property color checkOn:       textPrimary
    readonly property color checkOnBorder: textPrimary
    readonly property color checkMark:     surface
    readonly property color noteBg:   dark ? "#2E2A16" : "#FFFBEA"   // field has a note (req 10)

    readonly property color consoleBg:   "#141414"
    readonly property color consoleText: "#D8D8D8"
    readonly property color overlay:     dark ? "#99000000" : "#59111111"

    // spacing, shape, type
    readonly property int s1: 4
    readonly property int s2: 8
    readonly property int s3: 12
    readonly property int s4: 16
    readonly property int s6: 24
    readonly property int radius: 8
    readonly property int radiusSm: 6
    readonly property int rowHeight: 28
    readonly property int headerHeight: 44

    readonly property string fontUi: "Segoe UI"
    readonly property string fontMono: "Consolas"
    readonly property string fontIcons: "Segoe MDL2 Assets"

    // One knob for every text and icon size in the app. 1.0 = the original design;
    // 130/175 makes text look like Windows 130% scaling on a 175% display.
    property real fontScale: 130 / 175
    function px(size) { return Math.max(7, Math.round(size * fontScale)) }

    readonly property int fontTiny: px(10)      // bit numbers
    readonly property int fontXs: px(11)        // helper text, chips, table headers
    readonly property int fontSm: px(12)        // buttons, secondary text
    readonly property int fontMd: px(13)        // body text
    readonly property int fontValue: px(14)     // register value field
    readonly property int fontHeading: px(15)   // dialog titles, app name
    readonly property int fontLg: px(16)        // empty-state titles
    readonly property int fontTitle: px(17)     // register name in the detail header
    readonly property int fontDisplay: px(20)   // chip family ("LION A0"), peripheral title
    readonly property int fontXl: px(22)        // stat tiles

    function toneBg(tone) {
        return ({ info: infoBg, ok: okBg, warn: warnBg, danger: dangerBg, split: splitBg })[tone] || select
    }
    function toneFg(tone) {
        return ({ info: infoFg, ok: okFg, warn: warnFg, danger: dangerFg, split: splitFg })[tone] || textMuted
    }
    // access type -> tone (req 7 semantics)
    function accessTone(key) {
        return ({ ro: "info", rw: "ok", wo: "danger", w1: "warn", rw1: "split" })[key] || "mute"
    }
    // operation kind -> tone
    function kindTone(kind) {
        return ({ register_write: "ok", field_write: "ok", rf_switch: "split", load_phy: "info",
                  signal_generator: "warn", gfsk_packet: "warn" })[kind] || "mute"
    }
    // action/operation type colors (req 13: "Items colored by type")
    function kindColor(kind) {
        var light = { custom_function: "#E8590C", rf_switch: "#7950F2", signal_generator: "#0C8599",
                      gfsk_packet: "#0C8599", load_phy: "#1C7ED6", load_wifi_phy: "#1098AD",
                      dut_control_method: "#C2255C", dut_reconnect: "#2B8A3E", sequence: "#862E9C",
                      prs_route: "#5F3DC4" }
        var darkColors = { custom_function: "#FF922B", rf_switch: "#9775FA", signal_generator: "#3BC9DB",
                           gfsk_packet: "#3BC9DB", load_phy: "#4DABF7", load_wifi_phy: "#66D9E8",
                           dut_control_method: "#F06595", dut_reconnect: "#69DB7C", sequence: "#DA77F2",
                           prs_route: "#B197FC" }
        return (dark ? darkColors : light)[kind] || textMuted
    }
    function logColor(level) {
        return ({ error: dangerFg, warning: warnFg, success: okFg })[level] || textMuted
    }
}
