import QtQuick 2.15
import "../theme"

// Minimal line plot for trends and the data logger. Auto-scales to the visible points.
Canvas {
    id: canvas
    property var points: []
    property color lineColor: Theme.textPrimary
    property real lineWidth: 1.5

    onPointsChanged: requestPaint()
    onLineColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var pts = points || []
        if (pts.length < 2)
            return
        var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts)
        var span = (hi - lo) || 1
        var pad = lineWidth + 1
        ctx.strokeStyle = lineColor
        ctx.lineWidth = lineWidth
        ctx.lineJoin = "round"
        ctx.beginPath()
        for (var i = 0; i < pts.length; i++) {
            var x = pad + (width - 2 * pad) * i / (pts.length - 1)
            var y = pad + (height - 2 * pad) * (1 - (pts[i] - lo) / span)
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.stroke()
    }
}
