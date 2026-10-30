import QtQuick 2.15
import "../theme"

// Time-series plot for the data logger (req 17): grid, axis ticks and labels, auto-range,
// drag to zoom (rectangle zoom on X), double-click to reset. xMin/xMax come from outside so
// every plot can share one X range (linked axes); -1 means auto.
Item {
    id: plot
    property var samples: []     // x values (sample numbers)
    readonly property int strokeRun: 24
    property var points: []      // y values
    property real xMin: -1
    property real xMax: -1
    property string xLabel: "Sample number"
    property string yLabel: ""
    property color lineColor: Theme.infoFg
    property real lineWidth: 2
    property var markers: []     // x positions of vertical marker lines (ECA trigger and markers A/B)
    property real minXStep: 1    // smallest x tick step; sample numbers are whole, ms aren't
    signal zoomRequested(real from, real to)
    signal resetRequested()

    readonly property int marginLeft: 56
    readonly property int marginRight: 10
    readonly property int marginTop: 8
    readonly property int marginBottom: 34
    readonly property real plotWidth: Math.max(1, width - marginLeft - marginRight)
    readonly property real plotHeight: Math.max(1, height - marginTop - marginBottom)

    // visible X range, auto when not zoomed
    readonly property real x0: xMin >= 0 ? xMin : (samples.length ? samples[0] : 0)
    readonly property real x1: {
        var hi = xMax >= 0 ? xMax : (samples.length ? samples[samples.length - 1] : 1)
        return hi > x0 ? hi : x0 + 1
    }

    function niceStep(span, targetTicks) {
        var raw = span / targetTicks
        var magnitude = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10))
        var steps = [1, 2, 2.5, 5, 10]
        for (var i = 0; i < steps.length; i++)
            if (steps[i] * magnitude >= raw) return steps[i] * magnitude
        return 10 * magnitude
    }
    // Tick labels show as many decimals as the tick step needs, so close ticks stay distinct.
    function label(v, step) {
        if (Math.abs(v) < step * 1e-6) return "0"
        if (Math.abs(v) >= 1e7) return v.toExponential(2)
        var decimals = 0
        while (decimals < 6 && Math.abs(step * Math.pow(10, decimals) - Math.round(step * Math.pow(10, decimals))) > 1e-6) decimals++
        return v.toFixed(decimals)
    }
    function sampleAt(px) {
        return x0 + (px - marginLeft) / plotWidth * (x1 - x0)
    }

    // Hidden plots skip the work; they catch up when they show again
    function repaint() {
        if (visible) canvas.requestPaint()
    }
    onVisibleChanged: repaint()
    onSamplesChanged: repaint()
    onPointsChanged: repaint()
    onX0Changed: repaint()
    onX1Changed: repaint()
    onMarkersChanged: repaint()
    onWidthChanged: repaint()
    onHeightChanged: repaint()
    property bool darkTheme: Theme.dark
    onDarkThemeChanged: repaint()

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: Theme.surface
        border.color: Theme.border
    }

    Canvas {
        id: canvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var L = plot.marginLeft, T = plot.marginTop, W = plot.plotWidth, H = plot.plotHeight
            var xs = plot.samples || [], ys = plot.points || []

            // y range from the points inside the visible x range
            var lo = Infinity, hi = -Infinity
            for (var i = 0; i < xs.length; i++) {
                if (xs[i] < plot.x0 || xs[i] > plot.x1) continue
                lo = Math.min(lo, ys[i]); hi = Math.max(hi, ys[i])
            }
            if (lo === Infinity) { lo = 0; hi = 1 }
            if (hi - lo < 1e-9) { lo -= 0.5; hi += 0.5 }
            var pad = (hi - lo) * 0.08
            lo -= pad; hi += pad

            function px(x) { return L + (x - plot.x0) / (plot.x1 - plot.x0) * W }
            function py(y) { return T + (1 - (y - lo) / (hi - lo)) * H }

            ctx.font = Theme.fontTiny + "px \"" + Theme.fontMono + "\""
            ctx.lineWidth = 1

            // grid + tick labels
            var yStep = plot.niceStep(hi - lo, 4)
            ctx.textAlign = "right"; ctx.textBaseline = "middle"
            for (var y = Math.ceil(lo / yStep) * yStep; y <= hi; y += yStep) {
                ctx.strokeStyle = Theme.border
                ctx.beginPath(); ctx.moveTo(L, Math.round(py(y)) + 0.5); ctx.lineTo(L + W, Math.round(py(y)) + 0.5); ctx.stroke()
                ctx.fillStyle = Theme.textMuted
                ctx.fillText(plot.label(y, yStep), L - 6, py(y))
            }
            var xStep = Math.max(plot.minXStep, plot.niceStep(plot.x1 - plot.x0, 6))
            ctx.textAlign = "center"; ctx.textBaseline = "top"
            for (var x = Math.ceil(plot.x0 / xStep) * xStep; x <= plot.x1; x += xStep) {
                ctx.strokeStyle = Theme.border
                ctx.beginPath(); ctx.moveTo(Math.round(px(x)) + 0.5, T); ctx.lineTo(Math.round(px(x)) + 0.5, T + H); ctx.stroke()
                ctx.fillStyle = Theme.textMuted
                ctx.fillText(plot.label(x, xStep), px(x), T + H + 4)
            }

            // axes
            ctx.strokeStyle = Theme.borderStrong
            ctx.beginPath(); ctx.moveTo(L + 0.5, T); ctx.lineTo(L + 0.5, T + H + 0.5); ctx.lineTo(L + W, T + H + 0.5); ctx.stroke()

            // axis labels
            ctx.fillStyle = Theme.textMuted
            ctx.font = Theme.fontTiny + "px \"" + Theme.fontUi + "\""
            ctx.textAlign = "center"; ctx.textBaseline = "bottom"
            ctx.fillText(plot.xLabel, L + W / 2, plot.height - 2)
            ctx.save()
            ctx.translate(10, T + H / 2); ctx.rotate(-Math.PI / 2)
            ctx.textBaseline = "middle"
            ctx.fillText(plot.yLabel, 0, 0)
            ctx.restore()

            // data
            if (xs.length === 0) {
                ctx.textBaseline = "middle"
                ctx.fillText("Waiting for samples", L + W / 2, T + H / 2)
                return
            }
            ctx.save()
            ctx.beginPath(); ctx.rect(L, T, W, H); ctx.clip()
            ctx.strokeStyle = plot.lineColor
            ctx.lineWidth = plot.lineWidth
            ctx.lineJoin = "round"
            // Stroked in short runs: one long path that crosses itself (noisy data) costs far more to paint
            for (var k = 0; k < xs.length - 1; k += plot.strokeRun) {
                ctx.beginPath()
                ctx.moveTo(px(xs[k]), py(ys[k]))
                for (var j = k + 1; j <= Math.min(k + plot.strokeRun, xs.length - 1); j++)
                    ctx.lineTo(px(xs[j]), py(ys[j]))
                ctx.stroke()
            }
            var marks = plot.markers || []
            ctx.lineWidth = 1
            if (ctx.setLineDash) ctx.setLineDash([4, 3])
            for (var m = 0; m < marks.length; m++) {
                ctx.strokeStyle = m === 0 ? Theme.textMuted : Theme.warnFg
                ctx.beginPath(); ctx.moveTo(Math.round(px(marks[m])) + 0.5, T); ctx.lineTo(Math.round(px(marks[m])) + 0.5, T + H); ctx.stroke()
            }
            if (ctx.setLineDash) ctx.setLineDash([])
            if (xs.length === 1) {
                ctx.fillStyle = plot.lineColor
                ctx.beginPath(); ctx.arc(px(xs[0]), py(ys[0]), 2.5, 0, 2 * Math.PI); ctx.fill()
            }
            ctx.restore()
        }
    }

    // rectangle zoom on X; double-click resets
    Rectangle {
        id: band
        visible: false
        y: plot.marginTop
        height: plot.plotHeight
        color: Theme.infoBg
        opacity: 0.6
        border.color: Theme.infoFg
    }
    MouseArea {
        id: zoomArea
        objectName: "plotZoomArea"
        x: plot.marginLeft
        y: plot.marginTop
        width: plot.plotWidth
        height: plot.plotHeight
        cursorShape: Qt.CrossCursor
        property real startX: 0
        onPressed: { startX = mouse.x; band.x = plot.marginLeft + mouse.x; band.width = 0; band.visible = true }
        onPositionChanged: {
            var a = Math.max(0, Math.min(startX, mouse.x)), b = Math.min(width, Math.max(startX, mouse.x))
            band.x = plot.marginLeft + a; band.width = b - a
        }
        onReleased: {
            band.visible = false
            if (Math.abs(mouse.x - startX) > 6)
                plot.zoomRequested(plot.sampleAt(plot.marginLeft + startX), plot.sampleAt(plot.marginLeft + mouse.x))
        }
        onDoubleClicked: plot.resetRequested()
    }
}
