"""调音台用的自绘控件：角色主视觉、角色卡、录音键、电平表、开关。尺寸都用逻辑像素，随系统缩放。"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import theme


# ---- 图案 -------------------------------------------------------------------
def _pen(color, width) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def paint_mic(p: QPainter, rect: QRectF, color: QColor) -> None:
    """麦克风：100×100 的坐标系缩放到 rect。"""
    p.save()
    p.translate(rect.x(), rect.y())
    p.scale(rect.width() / 100, rect.height() / 100)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(35, 8, 30, 50), 15, 15)
    shade = QColor(0, 0, 0, 50)
    p.setPen(_pen(shade, 2.4))
    for y in (22, 30, 38):
        p.drawLine(QPointF(42, y), QPointF(58, y))
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(color, 6))
    holder = QPainterPath()
    holder.moveTo(24, 42)
    holder.arcTo(QRectF(24, 18, 52, 52), 180, 180)
    p.drawPath(holder)
    p.drawLine(QPointF(50, 70), QPointF(50, 86))
    p.drawLine(QPointF(34, 89), QPointF(66, 89))
    p.restore()


def paint_guitar(p: QPainter, rect: QRectF, color: QColor) -> None:
    """吉他：琴身、琴颈、琴头，整体倾斜。"""
    p.save()
    p.translate(rect.center())
    p.scale(rect.width() / 100, rect.height() / 100)
    p.rotate(38)
    p.translate(-50, -52)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    body = QPainterPath()
    body.addEllipse(QPointF(50, 76), 21, 19)
    upper = QPainterPath()
    upper.addEllipse(QPointF(50, 53), 14.5, 13)
    p.drawPath(body.united(upper))
    p.drawRoundedRect(QRectF(46.5, 6, 7, 40), 2, 2)
    p.drawRoundedRect(QRectF(43, -4, 14, 14), 4, 4)
    shade = QColor(0, 0, 0, 70)
    p.setBrush(shade)
    p.drawEllipse(QPointF(50, 66), 6.5, 6.5)
    p.drawRoundedRect(QRectF(42, 82, 16, 4), 2, 2)
    p.setPen(_pen(shade, 1.2))
    for x in (48.5, 51.5):
        p.drawLine(QPointF(x, 8), QPointF(x, 82))
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    for y in (-1, 6):
        p.drawEllipse(QPointF(40.5, y), 2.2, 2.2)
        p.drawEllipse(QPointF(59.5, y), 2.2, 2.2)
    p.restore()


def paint_note(p: QPainter, rect: QRectF, color: QColor) -> None:
    p.save()
    p.translate(rect.x(), rect.y())
    p.scale(rect.width() / 100, rect.height() / 100)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(34, 74), 13, 10)
    p.drawEllipse(QPointF(72, 64), 13, 10)
    p.setPen(_pen(color, 6))
    p.drawLine(QPointF(44, 74), QPointF(44, 24))
    p.drawLine(QPointF(82, 64), QPointF(82, 14))
    p.drawLine(QPointF(44, 24), QPointF(82, 14))
    p.restore()


ART_PAINTERS = {"mic": paint_mic, "guitar": paint_guitar, "note": paint_note}


def paint_voice_art(p: QPainter, rect: QRectF, style: theme.VoiceStyle, pixmap: QPixmap | None,
                    radius: float) -> None:
    """在 rect 里画角色美术：有头像就完整显示整张图，否则画角色色舞台和图案。"""
    clip = QPainterPath()
    clip.addRoundedRect(rect, radius, radius)
    p.save()
    p.setClipPath(clip)
    if style.art == "avatar" and pixmap is not None and not pixmap.isNull():
        p.fillRect(rect, QColor(theme.NAVY_700))
        # 等比缩放并完整显示，不裁掉面部
        scale = min(rect.width() / pixmap.width(), rect.height() / pixmap.height())
        w, h = pixmap.width() * scale, pixmap.height() * scale
        target = QRectF(rect.center().x() - w / 2, rect.center().y() - h / 2, w, h)
        p.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
    else:
        color = QColor(style.color)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, color.darker(135))
        gradient.setColorAt(1, QColor(theme.NAVY_700))
        p.fillRect(rect, gradient)
        glow = QRadialGradient(rect.center(), rect.width() * 0.55)
        glow.setColorAt(0, QColor(255, 255, 255, 70))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(rect, glow)
        ring = QColor(style.accent)
        ring.setAlpha(90)
        p.setPen(_pen(ring, max(1.5, rect.width() * 0.012)))
        p.setBrush(Qt.NoBrush)
        for factor in (0.34, 0.44):
            p.drawEllipse(rect.center(), rect.width() * factor, rect.width() * factor)
        side = rect.width() * 0.56
        art = QRectF(rect.center().x() - side / 2, rect.center().y() - side / 2, side, side)
        painter = ART_PAINTERS.get(style.art, paint_note)
        painter(p, art.translated(side * 0.03, side * 0.04), QColor(0, 0, 0, 60))
        painter(p, art, QColor(theme.CREAM))
    p.restore()


def make_icon(kind: str, color: str, size: int = 18) -> QIcon:
    """播放/停止等小图标，按 3 倍像素画，缩放后保持清晰。"""
    ratio = 3
    pixmap = QPixmap(size * ratio, size * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    s = float(size)
    if kind == "play":
        path = QPainterPath()
        path.moveTo(s * 0.28, s * 0.16)
        path.lineTo(s * 0.84, s * 0.5)
        path.lineTo(s * 0.28, s * 0.84)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "stop":
        p.drawRoundedRect(QRectF(s * 0.22, s * 0.22, s * 0.56, s * 0.56), s * 0.1, s * 0.1)
    elif kind == "headphones":
        p.setBrush(Qt.NoBrush)
        p.setPen(_pen(color, s * 0.11))
        arc = QPainterPath()
        arc.moveTo(s * 0.18, s * 0.6)
        arc.arcTo(QRectF(s * 0.18, s * 0.16, s * 0.64, s * 0.74), 180, -180)
        p.drawPath(arc)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(s * 0.1, s * 0.52, s * 0.2, s * 0.34), s * 0.07, s * 0.07)
        p.drawRoundedRect(QRectF(s * 0.7, s * 0.52, s * 0.2, s * 0.34), s * 0.07, s * 0.07)
    p.end()
    return QIcon(pixmap)


# ---- 控件 -------------------------------------------------------------------
class Panel(QFrame):
    """带标题的调音台分区。"""

    def __init__(self, title: str = "", hint: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 12)
        outer.setSpacing(8)
        self.header = QHBoxLayout()
        self.header.setSpacing(10)
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("panelTitle")
            self.header.addWidget(self.title_label)
            self.hint_label = QLabel(hint)
            self.hint_label.setObjectName("panelHint")
            self.header.addWidget(self.hint_label, 1)
            outer.addLayout(self.header)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)


class ConsoleCombo(QComboBox):
    """下拉框，自己画箭头，长设备名在列表里完整显示。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(12)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.view().setTextElideMode(Qt.ElideNone)

    def showPopup(self):
        width = max((self.fontMetrics().horizontalAdvance(self.itemText(i)) for i in range(self.count())),
                    default=0) + 40
        self.view().setMinimumWidth(max(self.width(), width))
        super().showPopup()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(_pen(theme.SAKURA if self.isEnabled() else theme.DIM, 1.8))
        cx, cy = self.width() - 16, self.height() / 2
        p.drawLine(QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2.5))
        p.drawLine(QPointF(cx, cy + 2.5), QPointF(cx + 4, cy - 2))


class HeroArt(QWidget):
    """当前角色的主视觉。"""

    def __init__(self, side: int = 280, parent=None):
        super().__init__(parent)
        self._style = theme.voice_style("taffy")
        self._pixmap: QPixmap | None = None
        self._on_air = False
        self.setMinimumSize(200, 200)
        self._side = side
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self) -> QSize:
        return QSize(self._side, self._side)

    def set_voice(self, style: theme.VoiceStyle, pixmap: QPixmap | None) -> None:
        self._style, self._pixmap = style, pixmap
        self.update()

    def set_on_air(self, on_air: bool) -> None:
        if on_air != self._on_air:
            self._on_air = on_air
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        side = min(self.width(), self.height()) - 10
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        radius = side * 0.085
        # 向日葵黄的外框，监听时变成直播红
        frame = QColor(theme.DANGER if self._on_air else self._style.accent)
        p.setPen(Qt.NoPen)
        p.setBrush(frame)
        p.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), radius + 4, radius + 4)
        p.setBrush(QColor(theme.NAVY_900))
        p.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), radius + 1.5, radius + 1.5)
        paint_voice_art(p, rect, self._style, self._pixmap, radius)


class VoiceThumb(QWidget):
    def __init__(self, style: theme.VoiceStyle, pixmap: QPixmap | None, side: int = 56, parent=None):
        super().__init__(parent)
        self._style, self._pixmap = style, pixmap
        self.setFixedSize(side, side)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        paint_voice_art(p, rect, self._style, self._pixmap, rect.width() * 0.22)


class VoiceCard(QFrame):
    """一位角色：缩略图、名字、角色色，以及立即播放示例的按钮。"""

    chosen = Signal(str)
    preview_requested = Signal(str)

    def __init__(self, voice_id: str, name: str, pixmap: QPixmap | None, has_preview: bool, parent=None):
        super().__init__(parent)
        self.voice_id = voice_id
        self.name = name
        self.style_ = theme.voice_style(voice_id)
        self._active = False
        self.setObjectName("voiceCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(f"角色 {name}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(5)
        self.thumb = VoiceThumb(self.style_, pixmap)
        layout.addWidget(self.thumb, 0, Qt.AlignHCenter)
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-weight: 700; font-size: 10pt; background: transparent; border: none;")
        layout.addWidget(self.name_label)
        self.id_label = QLabel(voice_id.upper())
        self.id_label.setAlignment(Qt.AlignCenter)
        self.id_label.setStyleSheet(
            f"color: {self.style_.color}; font-size: 8pt; font-weight: 700; background: transparent; border: none;"
            'font-family: "Segoe UI", sans-serif;')
        layout.addWidget(self.id_label)
        self.preview_button = QPushButton("示例")
        self.preview_button.setObjectName("ghost")
        self.preview_button.setIconSize(QSize(12, 12))
        self.preview_button.setCursor(Qt.PointingHandCursor)
        self.preview_button.setEnabled(has_preview)
        self.preview_button.setToolTip(f"播放 {name} 的示例" if has_preview else "assets/previews 下没有这位角色的示例")
        self.preview_button.clicked.connect(lambda: self.preview_requested.emit(self.voice_id))
        layout.addWidget(self.preview_button)
        self.set_previewing(False)
        self._restyle()

    def set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self._restyle()

    def set_previewing(self, playing: bool) -> None:
        self.preview_button.setText("停止" if playing else "示例")
        self.preview_button.setIcon(make_icon("stop" if playing else "play", self.style_.color, 12))

    def _restyle(self) -> None:
        color = self.style_.color
        if self._active:
            tint = QColor(color)
            tint.setAlpha(46)
            background = f"rgba({tint.red()},{tint.green()},{tint.blue()},{tint.alpha()})"
            border = f"2px solid {color}"
        else:
            background = theme.NAVY_900
            border = f"1px solid {theme.NAVY_600}"
        self.setStyleSheet(
            f"QFrame#voiceCard {{ background: {background}; border: {border}; border-radius: 12px; }}"
            f"QFrame#voiceCard:hover {{ border-color: {color}; }}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.chosen.emit(self.voice_id)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.chosen.emit(self.voice_id)
        else:
            super().keyPressEvent(event)


class RecButton(QAbstractButton):
    """录音键。未按下是红色圆点，录音中是方块加脉动光环。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(76, 76)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("录音")
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        if checked:
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.08) % 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 3
        enabled = self.isEnabled()
        red = QColor(theme.DANGER if enabled else theme.DIM)
        if self.isChecked():
            glow = QColor(theme.DANGER)
            glow.setAlpha(int(110 * (1 - self._phase)))
            p.setPen(_pen(glow, 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(center, radius - 6 + 7 * self._phase, radius - 6 + 7 * self._phase)
        p.setPen(_pen(theme.CREAM if enabled else theme.DIM, 3))
        p.setBrush(QColor(theme.NAVY_900))
        p.drawEllipse(center, radius - 7, radius - 7)
        p.setPen(Qt.NoPen)
        p.setBrush(red.lighter(115) if self.underMouse() and enabled else red)
        if self.isChecked():
            half = radius * 0.3
            p.drawRoundedRect(QRectF(center.x() - half, center.y() - half, half * 2, half * 2), 5, 5)
        else:
            p.drawEllipse(center, radius * 0.5, radius * 0.5)
        if self.hasFocus():
            p.setPen(_pen(theme.SKY, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(center, radius, radius)


class LevelMeter(QWidget):
    """分段电平表，输入峰值 0–1，按 dB 显示并缓慢回落。"""

    SEGMENTS = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self.setMinimumSize(120, 12)
        self.setMaximumHeight(14)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_peak(self, peak: float) -> None:
        level = 0.0 if peak <= 1e-4 else max(0.0, min(1.0, 1 + 20 * math.log10(peak) / 48))
        value = max(level, self._value - 0.06)
        if abs(value - self._value) > 1e-3:
            self._value = value
            self.update()

    def reset(self) -> None:
        self._value = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        gap = 3.0
        width = (self.width() - gap * (self.SEGMENTS - 1)) / self.SEGMENTS
        lit = round(self._value * self.SEGMENTS)
        p.setPen(Qt.NoPen)
        for i in range(self.SEGMENTS):
            if i < lit:
                color = QColor(theme.DANGER if i >= self.SEGMENTS - 2 else
                               theme.SUNFLOWER if i >= self.SEGMENTS - 6 else theme.SAKURA)
            else:
                color = QColor(theme.NAVY_600)
                color.setAlpha(120)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(i * (width + gap), 1, width, self.height() - 2), 2, 2)


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(64, 34)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        enabled = self.isEnabled()
        if self.isChecked():
            track = QColor(theme.DANGER if enabled else theme.NAVY_600)
        else:
            track = QColor(theme.NAVY_900)
        p.setPen(_pen(theme.SAKURA if enabled else theme.NAVY_600, 1.5))
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        knob = rect.height() - 8
        x = rect.right() - knob - 4 if self.isChecked() else rect.left() + 4
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.CREAM if enabled else theme.DIM))
        p.drawEllipse(QRectF(x, rect.top() + 4, knob, knob))
        if self.hasFocus():
            p.setPen(_pen(theme.SKY, 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 17, 17)


def set_state(widget: QWidget, state: str) -> None:
    """改动态属性 state 并让样式表重新生效。"""
    if widget.property("state") != state:
        widget.setProperty("state", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
