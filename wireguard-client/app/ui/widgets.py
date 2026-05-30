"""Custom animated widgets: pulsing status dot, sparkline, power button.

These are self-contained ``QWidget`` subclasses that paint themselves and run
their own animations, so the rest of the UI stays declarative.
"""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QAbstractButton, QWidget


def _alpha(color: QColor | str, alpha: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


class PulseDot(QWidget):
    """A small status dot that emits an expanding, fading ring when active."""

    def __init__(self, parent: QWidget | None = None, diameter: int = 12) -> None:
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter * 2, diameter * 2)
        self._color = QColor("#9b97ad")
        self._active = False
        self._phase = 0.0
        self._anim = QPropertyAnimation(self, b"phase", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1600)
        self._anim.setLoopCount(-1)

    def get_phase(self) -> float:
        return self._phase

    def set_phase(self, value: float) -> None:
        self._phase = value
        self.update()

    phase = Property(float, get_phase, set_phase)

    def set_color(self, color: QColor | str) -> None:
        self._color = QColor(color)
        self.update()

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        if active:
            self._anim.start()
        else:
            self._anim.stop()
            self._phase = 0.0
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        core = self._d * 0.42
        if self._active:
            ring = core + (self._d * 0.9) * self._phase
            p.setPen(Qt.NoPen)
            p.setBrush(_alpha(self._color, 0.45 * (1.0 - self._phase)))
            p.drawEllipse(QPointF(cx, cy), ring, ring)
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), core, core)
        p.end()


class Sparkline(QWidget):
    """A compact filled area chart fed with a rolling series of values."""

    def __init__(self, parent: QWidget | None = None, capacity: int = 48) -> None:
        super().__init__(parent)
        self._data: deque[float] = deque([0.0] * capacity, maxlen=capacity)
        self._color = QColor("#7d4dff")
        self.setMinimumHeight(40)

    def set_color(self, color: QColor | str) -> None:
        self._color = QColor(color)
        self.update()

    def push(self, value: float) -> None:
        self._data.append(max(0.0, float(value)))
        self.update()

    def reset(self) -> None:
        self._data = deque([0.0] * self._data.maxlen, maxlen=self._data.maxlen)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        data = list(self._data)
        peak = max(data) or 1.0
        n = len(data)
        if n < 2:
            p.end()
            return
        step = w / (n - 1)
        pad = 3.0
        usable = h - pad * 2

        pts = [
            QPointF(i * step, h - pad - (v / peak) * usable)
            for i, v in enumerate(data)
        ]

        line = QPainterPath()
        line.moveTo(pts[0])
        for i in range(1, n):
            prev, cur = pts[i - 1], pts[i]
            mx = (prev.x() + cur.x()) / 2
            line.cubicTo(mx, prev.y(), mx, cur.y(), cur.x(), cur.y())

        fill = QPainterPath(line)
        fill.lineTo(pts[-1].x(), h)
        fill.lineTo(pts[0].x(), h)
        fill.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, _alpha(self._color, 0.40))
        grad.setColorAt(1.0, _alpha(self._color, 0.02))
        p.fillPath(fill, grad)

        p.setPen(QPen(self._color, 2.0))
        p.drawPath(line)
        p.end()


class PowerButton(QAbstractButton):
    """A large circular power button with press, connect and pulse animations.

    States: ``"off"`` (idle), ``"connecting"`` (spinner), ``"on"`` (glowing).
    """

    def __init__(self, parent: QWidget | None = None, diameter: int = 168) -> None:
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.PointingHandCursor)
        self._state = "off"
        self._accent = QColor("#7d4dff")
        self._green = QColor("#1ea885")
        self._muted = QColor("#9b97ad")
        self._ring_bg = QColor("#2a2738")

        self._scale = 1.0
        self._pulse = 0.0
        self._spin = 0.0

        self._scale_anim = QPropertyAnimation(self, b"scale", self)
        self._scale_anim.setDuration(140)
        self._scale_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._pulse_anim = QPropertyAnimation(self, b"pulse", self)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(1900)
        self._pulse_anim.setLoopCount(-1)

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(16)
        self._spin_timer.timeout.connect(self._advance_spin)

    # -- animated properties ----------------------------------------------------
    def get_scale(self) -> float:
        return self._scale

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.update()

    scale = Property(float, get_scale, set_scale)

    def get_pulse(self) -> float:
        return self._pulse

    def set_pulse(self, value: float) -> None:
        self._pulse = value
        self.update()

    pulse = Property(float, get_pulse, set_pulse)

    def _advance_spin(self) -> None:
        self._spin = (self._spin + 6.0) % 360.0
        self.update()

    # -- public API -------------------------------------------------------------
    def set_colors(self, accent, green, muted, ring_bg) -> None:
        self._accent = QColor(accent)
        self._green = QColor(green)
        self._muted = QColor(muted)
        self._ring_bg = QColor(ring_bg)
        self.update()

    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self._pulse_anim.stop()
        self._spin_timer.stop()
        if state == "on":
            self._pulse = 0.0
            self._pulse_anim.start()
        elif state == "connecting":
            self._spin = 0.0
            self._spin_timer.start()
        self.update()

    # -- interaction ------------------------------------------------------------
    def _animate_scale(self, target: float) -> None:
        self._scale_anim.stop()
        self._scale_anim.setStartValue(self._scale)
        self._scale_anim.setEndValue(target)
        self._scale_anim.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._animate_scale(0.93)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._animate_scale(1.0)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        if not self.isDown():
            self._animate_scale(1.04)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._animate_scale(1.0)
        super().leaveEvent(event)

    # -- painting ---------------------------------------------------------------
    def _main_color(self) -> QColor:
        if self._state == "on":
            return self._green
        if self._state == "connecting":
            return self._accent
        return self._accent

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = self._d
        p.translate(side / 2, side / 2)
        p.scale(self._scale, self._scale)
        p.translate(-side / 2, -side / 2)

        color = self._main_color()
        cx = cy = side / 2
        base_r = side * 0.30

        # outward pulse halo when connected
        if self._state == "on":
            for k in (0.0, 0.5):
                ph = (self._pulse + k) % 1.0
                r = base_r + (side * 0.20) * ph
                p.setPen(Qt.NoPen)
                p.setBrush(_alpha(color, 0.28 * (1.0 - ph)))
                p.drawEllipse(QPointF(cx, cy), r, r)

        # track ring
        track = QRectF(side * 0.16, side * 0.16, side * 0.68, side * 0.68)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self._ring_bg, side * 0.045))
        p.drawEllipse(track)

        # progress / accent arc
        if self._state == "connecting":
            pen = QPen(color, side * 0.045)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            start = int(-self._spin * 16)
            p.drawArc(track, start, 90 * 16)
        elif self._state == "on":
            pen = QPen(color, side * 0.045)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(track, 90 * 16, 360 * 16)

        # inner filled disc
        grad = QLinearGradient(0, side * 0.2, 0, side * 0.8)
        grad.setColorAt(0.0, _alpha(color, 0.95 if self._state != "off" else 0.85))
        grad.setColorAt(1.0, _alpha(color, 0.70 if self._state != "off" else 0.55))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        disc = base_r * 0.92
        p.drawEllipse(QPointF(cx, cy), disc, disc)

        # power glyph
        glyph_pen = QPen(QColor("#ffffff"), side * 0.035)
        glyph_pen.setCapStyle(Qt.RoundCap)
        p.setPen(glyph_pen)
        gr = side * 0.12
        arc = QRectF(cx - gr, cy - gr, gr * 2, gr * 2)
        p.drawArc(arc, 70 * 16, 320 * 16)
        p.drawLine(QPointF(cx, cy - gr * 1.25), QPointF(cx, cy + gr * 0.05))
        p.end()
