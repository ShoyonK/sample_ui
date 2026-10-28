"""Draws the SiRAT app icon (PNG for the window, ICO for the .exe). Re-run if the design changes.

    uv run python scripts/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath

ROOT = Path(__file__).resolve().parents[1]


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    p.fillPath(path, QColor("#111111"))
    # four "bit" cells along the bottom, the last two set, like the bit grid
    cell, gap = size * 0.13, size * 0.05
    x0 = (size - (4 * cell + 3 * gap)) / 2
    for i in range(4):
        rect = QRectF(x0 + i * (cell + gap), size * 0.68, cell, cell)
        p.setPen(QColor("#FFFFFF") if i < 2 else Qt.NoPen)
        p.setBrush(QColor("#FFFFFF") if i >= 2 else Qt.NoBrush)
        p.drawRoundedRect(rect, cell * 0.2, cell * 0.2)
    font = QFont("Segoe UI", -1, QFont.Bold)
    font.setPixelSize(int(size * 0.48))
    p.setFont(font)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(QRectF(0, size * 0.04, size, size * 0.62), Qt.AlignCenter, "S")
    p.end()
    return image


def main() -> None:
    app = QGuiApplication([])  # noqa: F841 (fonts need an application)
    png = ROOT / "src" / "sirat_ui" / "qml" / "assets" / "sirat.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    draw(256).save(str(png))
    ico = ROOT / "packaging" / "sirat.ico"
    ico.parent.mkdir(parents=True, exist_ok=True)
    draw(256).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(ico), "ICO")
    print("wrote", png, "and", ico)


if __name__ == "__main__":
    main()
