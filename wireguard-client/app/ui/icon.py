"""Programmatically drawn application / tray icon (no asset files needed)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

_POWER = "\u23fb"


def make_app_icon(connected: bool = False, size: int = 64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    color = QColor("#1ea885") if connected else QColor("#7d4dff")
    painter.setBrush(color)
    painter.setPen(Qt.NoPen)
    radius = size * 0.28
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    font = QFont()
    font.setPointSizeF(size * 0.5)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, _POWER)
    painter.end()
    return QIcon(pix)
