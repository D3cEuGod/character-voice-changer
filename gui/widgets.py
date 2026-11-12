"""自绘控件：角色主视觉、角色头像、变声开关、录音键、电平条。尺寸都用逻辑像素，随系统缩放。"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

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


def paint_voice_art(p: QPainter, clip: QPainterPath, rect: QRectF, style: theme.VoiceStyle,
                    pixmap: QPixmap | None) -> None:
    """在 clip 里画角色美术：有头像就完整显示整张图，没有就画角色色背景和图案。"""
    p.save()
    p.setClipPath(clip)
    if pixmap is not None and not pixmap.isNull():
        p.fillRect(rect, QColor(theme.RAISED))
        scale = max(rect.width() / pixmap.width(), rect.height() / pixmap.height())
        if abs(pixmap.width() - pixmap.height()) > 2:  # 非正方形的图等比缩小，完整保留面部
            scale = min(rect.width() / pixmap.width(), rect.height() / pixmap.height())
        w, h = pixmap.width() * scale, pixmap.height() * scale
        target = QRectF(rect.center().x() - w / 2, rect.center().y() - h / 2, w, h)
        p.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
    else:
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(style.color).darker(130))
        gradient.setColorAt(1, QColor(theme.RAISED))
        p.fillRect(rect, gradient)
        glow = QRadialGradient(rect.center(), rect.width() * 0.55)
        glow.setColorAt(0, QColor(255, 255, 255, 70))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(rect, glow)
        side = rect.width() * 0.56
        art = QRectF(rect.center().x() - side / 2, rect.center().y() - side / 2, side, side)
        ART_PAINTERS.get(style.art, paint_note)(p, art, QColor(theme.CREAM))
    p.restore()


def make_icon(kind: str, color: str, size: int = 18) -> QIcon:
    """播放、停止、刷新小图标，按 3 倍像素画，缩放后保持清晰。"""
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
    elif kind == "refresh":
        p.setBrush(Qt.NoBrush)
        p.setPen(_pen(color, s * 0.11))
        p.drawArc(QRectF(s * 0.2, s * 0.2, s * 0.6, s * 0.6), 40 * 16, 280 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        tip = QPainterPath()
        tip.moveTo(s * 0.86, s * 0.14)
        tip.lineTo(s * 0.86, s * 0.46)
        tip.lineTo(s * 0.56, s * 0.38)
        tip.closeSubpath()
        p.drawPath(tip)
    p.end()
    return QIcon(pixmap)


# ---- 控件 -------------------------------------------------------------------
class Card(QFrame):
    """一块圆角底板，内容放进 body。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(20, 18, 20, 18)
        self.body.setSpacing(12)


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


def label(text: str, name: str = "muted") -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(name)
    return widget


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
        p.setPen(_pen(theme.MUTED if self.isEnabled() else theme.DIM, 1.8))
        cx, cy = self.width() - 16, self.height() / 2
        p.drawLine(QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2.5))
        p.drawLine(QPointF(cx, cy + 2.5), QPointF(cx + 4, cy - 2))


class Segmented(QWidget):
    """两三个互斥选项排成一条。接口与下拉框一致：addItem、currentData、currentText、currentIndexChanged。"""

    currentIndexChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._data: list = []
        self._group.idToggled.connect(lambda index, checked: checked and self.currentIndexChanged.emit(index))

    def addItem(self, text: str, data=None) -> None:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        self._group.addButton(button, len(self._data))
        self._data.append(data)
        self._row.addWidget(button)
        buttons = self._group.buttons()
        for index, item in enumerate(buttons):
            item.setObjectName("segLeft" if index == 0 else "segRight" if index == len(buttons) - 1 else "segMiddle")
        if len(buttons) == 1:
            button.setChecked(True)

    def currentIndex(self) -> int:
        return self._group.checkedId()

    def setCurrentIndex(self, index: int) -> None:
        self._group.button(index).setChecked(True)

    def currentData(self):
        return self._data[self.currentIndex()] if self._data else None

    def findData(self, data) -> int:
        return self._data.index(data) if data in self._data else -1

    def currentText(self) -> str:
        button = self._group.checkedButton()
        return button.text() if button is not None else ""

    def button(self, index: int) -> QPushButton:
        return self._group.button(index)


class HeroArt(QWidget):
    """当前角色的主视觉，带角色色描边；变声进行时描边变成直播红。"""

    def __init__(self, side: int = 280, parent=None):
        super().__init__(parent)
        self._style = theme.voice_style("taffy")
        self._pixmap: QPixmap | None = None
        self._on_air = False
        self._side = side
        self.setMinimumSize(180, 180)
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
        side = min(self.width(), self.height()) - 8
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        radius = side * 0.11
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.DANGER if self._on_air else self._style.accent))
        p.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), radius + 3, radius + 3)
        clip = QPainterPath()
        clip.addRoundedRect(rect, radius, radius)
        paint_voice_art(p, clip, rect, self._style, self._pixmap)


class VoiceCard(QWidget):
    """一位角色：圆形头像、名字，以及立即播放示例的按钮。"""

    chosen = Signal(str)
    preview_requested = Signal(str)
    THUMB = 62

    def __init__(self, voice_id: str, name: str, pixmap: QPixmap | None, has_preview: bool, parent=None):
        super().__init__(parent)
        self.voice_id = voice_id
        self.name = name
        self.style_ = theme.voice_style(voice_id)
        self._pixmap = pixmap
        self._active = False
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(f"角色 {name}")
        self.setAttribute(Qt.WA_Hover)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, self.THUMB + 12, 4, 0)
        layout.setSpacing(2)
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)
        self.preview_button = QPushButton("示例")
        self.preview_button.setObjectName("ghost")
        self.preview_button.setIconSize(QSize(11, 11))
        self.preview_button.setCursor(Qt.PointingHandCursor)
        self.preview_button.setEnabled(has_preview)
        self.preview_button.setToolTip(f"播放 {name} 的示例" if has_preview else "assets/previews 下没有这位角色的示例")
        self.preview_button.clicked.connect(lambda: self.preview_requested.emit(self.voice_id))
        layout.addWidget(self.preview_button, 0, Qt.AlignHCenter)
        self.set_previewing(False)
        self._restyle()

    def set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self._restyle()
            self.update()

    def set_previewing(self, playing: bool) -> None:
        self.preview_button.setText("停止" if playing else "示例")
        self.preview_button.setIcon(make_icon("stop" if playing else "play", self.style_.color, 11))

    def _restyle(self) -> None:
        color = theme.CREAM if self._active else theme.MUTED
        self.name_label.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 10pt;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        side = self.THUMB
        rect = QRectF((self.width() - side) / 2, 6, side, side)
        if self._active or self._hover or self.hasFocus():
            ring = QColor(self.style_.color)
            ring.setAlpha(255 if self._active else 120)
            p.setPen(_pen(ring, 2.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(rect.adjusted(-4, -4, 4, 4))
        clip = QPainterPath()
        clip.addEllipse(rect)
        paint_voice_art(p, clip, rect, self.style_, self._pixmap)
        if not self._active:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(14, 21, 48, 70))
            p.drawEllipse(rect)

    def event(self, event):
        if event.type() in (event.Type.HoverEnter, event.Type.HoverLeave):
            self._hover = event.type() == event.Type.HoverEnter
            self.update()
        return super().event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.chosen.emit(self.voice_id)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.chosen.emit(self.voice_id)
        else:
            super().keyPressEvent(event)


class _PulseButton(QAbstractButton):
    """按下后带脉动光环的圆形开关。"""

    def __init__(self, side: int, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(side, side)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
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
        self._phase = (self._phase + 0.05) % 1.0
        self.update()


class LiveButton(_PulseButton):
    """实时变声的总开关：一个大圆键，打开后填充角色色。"""

    def __init__(self, parent=None):
        super().__init__(116, parent)
        self._color = QColor(theme.SAKURA)
        self.setAccessibleName("实时变声")

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = self.width() / 2 - 14
        enabled, on = self.isEnabled(), self.isChecked()
        if on:
            glow = QColor(self._color)
            glow.setAlpha(int(130 * (1 - self._phase)))
            p.setPen(_pen(glow, 3))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(center, radius + 2 + 11 * self._phase, radius + 2 + 11 * self._phase)
        if on:
            fill, ink, edge = self._color, QColor(theme.BACKGROUND), self._color
        elif enabled:
            fill, ink = QColor(theme.RAISED), QColor(theme.CREAM)
            edge = self._color if self.underMouse() or self.hasFocus() else QColor(theme.LINE)
        else:
            fill, ink, edge = QColor("#19224A"), QColor(theme.DIM), QColor("#19224A")
        p.setPen(_pen(edge, 2.5))
        p.setBrush(fill)
        p.drawEllipse(center, radius, radius)
        side = radius * 0.95
        paint_mic(p, QRectF(center.x() - side / 2, center.y() - side / 2, side, side), ink)


class RecButton(_PulseButton):
    """录音键。未按下是红色圆点，录音中是方块加脉动光环。"""

    def __init__(self, parent=None):
        super().__init__(64, parent)
        self.setAccessibleName("录音")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = self.width() / 2 - 8
        enabled = self.isEnabled()
        red = QColor(theme.DANGER if enabled else theme.DIM)
        if self.isChecked():
            glow = QColor(theme.DANGER)
            glow.setAlpha(int(120 * (1 - self._phase)))
            p.setPen(_pen(glow, 3))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(center, radius + 1 + 6 * self._phase, radius + 1 + 6 * self._phase)
        edge = theme.CREAM if enabled and (self.underMouse() or self.hasFocus() or self.isChecked()) else theme.LINE
        p.setPen(_pen(edge if enabled else theme.DIM, 2))
        p.setBrush(QColor(theme.FIELD))
        p.drawEllipse(center, radius, radius)
        p.setPen(Qt.NoPen)
        p.setBrush(red)
        if self.isChecked():
            half = radius * 0.36
            p.drawRoundedRect(QRectF(center.x() - half, center.y() - half, half * 2, half * 2), 4, 4)
        else:
            p.drawEllipse(center, radius * 0.56, radius * 0.56)


class LevelMeter(QWidget):
    """细长的电平条，输入峰值 0–1，按 dB 显示并缓慢回落。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self.setMinimumSize(80, 6)
        self.setMaximumHeight(6)
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
        rect = QRectF(self.rect())
        radius = rect.height() / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.FIELD))
        p.drawRoundedRect(rect, radius, radius)
        if self._value > 0.01:
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
            gradient.setColorAt(0, QColor(theme.SKY))
            gradient.setColorAt(0.7, QColor(theme.SAKURA))
            gradient.setColorAt(0.92, QColor(theme.SUNFLOWER))
            gradient.setColorAt(1, QColor(theme.DANGER))
            p.setBrush(gradient)
            p.setClipRect(QRectF(0, 0, rect.width() * self._value, rect.height()))
            p.drawRoundedRect(rect, radius, radius)


def set_state(widget: QWidget, state: str) -> None:
    """改动态属性 state 并让样式表重新生效。"""
    if widget.property("state") != state:
        widget.setProperty("state", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
