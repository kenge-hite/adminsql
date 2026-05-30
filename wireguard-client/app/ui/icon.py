"""Programmatically drawn application / tray icon (no asset files needed)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)


def make_app_icon(connected: bool = False, size: int = 64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    if connected:
        top, bottom = QColor("#27b893"), QColor("#0f9d76")
    else:
        top, bottom = QColor("#8d63ff"), QColor("#6d3df0")

    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, top)
    grad.setColorAt(1.0, bottom)
    painter.setBrush(grad)
    painter.setPen(Qt.NoPen)
    radius = size * 0.28
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # power glyph
    cx = cy = size / 2
    gr = size * 0.20
    pen = QPen(QColor("#ffffff"), size * 0.08)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    arc = QRectF(cx - gr, cy - gr, gr * 2, gr * 2)
    painter.drawArc(arc, 70 * 16, 320 * 16)
    painter.drawLine(QPointF(cx, cy - gr * 1.3), QPointF(cx, cy + gr * 0.05))
    painter.end()
    return QIcon(pix)
