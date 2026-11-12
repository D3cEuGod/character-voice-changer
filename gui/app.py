"""主窗口：二次元广播室的调音台。只在 QApplication 创建之后导入。"""
from __future__ import annotations

import io
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf
from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QVBoxLayout,
                               QWidget)

from . import audio, theme
from .backend import (CONTENT_TYPES, DEFAULT_URL, ROOT, START_SCRIPT, BackendClient, BackendError,
                      BackendLauncher, stop_process_tree)
from .live import LiveMonitor
from .widgets import (ConsoleCombo, HeroArt, LevelMeter, Panel, RecButton, ToggleSwitch, VoiceCard,
                      make_icon, set_state)

ASSETS = ROOT / "assets"
PREVIEWS = ASSETS / "previews"
MAX_RESULTS = 8


@dataclass
class Config:
    backend_url: str = DEFAULT_URL
    autostart: bool = True
    script: Path = START_SCRIPT


@dataclass
class InputClip:
    serial: int
    label: str
    data: bytes           # 原样提交给 POST /api/convert 的文件字节
    content_type: str
    samples: np.ndarray   # 本地试听用的单声道样本
    rate: int

    @property
    def seconds(self) -> float:
        return len(self.samples) / self.rate


@dataclass
class ResultClip:
    key: tuple            # (输入序号, voice_id, 强度百分比)：生成这段结果时的参数
    wav: bytes            # 后端返回的 WAV，另存时原样写出
    samples: np.ndarray
    rate: int
    voice_name: str
    input_label: str
    elapsed: float
    created: float = field(default_factory=time.time)


class Bridge(QObject):
    """工作线程通过这些信号把结果送回界面线程。"""

    backend_progress = Signal(str)
    backend_ready = Signal(object, object, bool)
    backend_failed = Signal(object, str)
    voices_loaded = Signal(object)
    voices_failed = Signal(str)
    health_result = Signal(bool, str)
    convert_done = Signal(object, object, float)
    convert_failed = Signal(object, str)
    live_connected = Signal(object, object)
    live_stats = Signal(object, object)
    live_stopped = Signal(object, str, str)


def _clock(seconds: float) -> str:
    seconds = max(0.0, seconds)
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


class MainWindow(QWidget):
    def __init__(self, config: Config | None = None):
        super().__init__()
        self.config = config or Config()
        self.client = BackendClient(self.config.backend_url)
        self.bridge = Bridge()

        self.backend_ok = False
        self.max_seconds = 60.0
        self.max_bytes = 24 * 1024 * 1024
        self.voices: list[dict] = []
        self.voice_id: str | None = None
        self.cards: dict[str, VoiceCard] = {}
        self.strength_pct = 100
        self.input: InputClip | None = None
        self.results: dict[tuple, ResultClip] = {}
        self.converting_key: tuple | None = None
        self.ab = "input"
        self.recorder: audio.Recorder | None = None
        self.player = audio.ClipPlayer()
        self.playing_tag: tuple | None = None
        self.live: LiveMonitor | None = None
        self.owned_backend = None

        self._serial = 0
        self._launcher: BackendLauncher | None = None
        self._health_inflight = False
        self._health_failures = 0
        self._convert_started = 0.0
        self._rec_started = 0.0
        self._live_restart = False
        self._live_stats: dict = {}
        self._closing = False
        self._last_dir = str(ROOT)
        avatar = QPixmap(str(ASSETS / "taffy-avatar.jpg"))
        self._avatar = None if avatar.isNull() else avatar

        self.setObjectName("root")
        self.setWindowTitle("角色变声器 · 广播室调音台")
        if self._avatar is not None:
            self.setWindowIcon(QIcon(self._avatar))
        self._build()
        self._wire()
        self._populate_devices(announce=False)
        self._show_voice(None)
        self._refresh()

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(40)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(3000)
        self._health_timer.timeout.connect(self._poll_health)
        self._health_timer.start()
        self._strength_timer = QTimer(self)
        self._strength_timer.setSingleShot(True)
        self._strength_timer.setInterval(450)
        self._strength_timer.timeout.connect(self._restart_live)

        QTimer.singleShot(0, self.connect_backend)

    # ---- 界面搭建 -------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("header")
        row = QHBoxLayout(header)
        row.setContentsMargins(16, 7, 16, 7)
        row.setSpacing(14)
        self.lamp = QLabel("STANDBY")
        self.lamp.setObjectName("lamp")
        self.lamp.setAlignment(Qt.AlignCenter)
        self.lamp.setMinimumWidth(84)
        row.addWidget(self.lamp)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("角色变声器")
        title.setObjectName("appTitle")
        subtitle = QLabel("广播室调音台 · RVC / So-VITS-SVC")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        row.addLayout(titles)
        row.addStretch(1)
        self.backend_pill = QLabel("后端：检查中")
        self.backend_pill.setObjectName("pill")
        row.addWidget(self.backend_pill)
        self.reconnect_button = QPushButton("重新连接")
        self.reconnect_button.setObjectName("ghost")
        self.reconnect_button.setToolTip("检查本地后端；没有运行时启动 start-backend.cmd")
        row.addWidget(self.reconnect_button)
        root.addWidget(header)

        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        self.notice.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.notice.hide()
        root.addWidget(self.notice)

        columns = QHBoxLayout()
        columns.setSpacing(12)
        columns.addWidget(self._build_cast(), 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        console = QWidget()
        stack = QVBoxLayout(console)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(10)
        stack.addWidget(self._build_devices())
        work = QHBoxLayout()
        work.setSpacing(10)
        work.addWidget(self._build_input(), 5)
        work.addWidget(self._build_mix(), 4)
        stack.addLayout(work)
        stack.addWidget(self._build_audition())
        stack.addWidget(self._build_live())
        stack.addStretch(1)
        scroll.setWidget(console)
        columns.addWidget(scroll, 1)
        root.addLayout(columns, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusBar")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.status_label)

    def _build_cast(self) -> QWidget:
        panel = Panel("当前角色", "点角色卡切换声线")
        panel.setFixedWidth(330)
        self.hero = HeroArt(286)
        panel.body.addWidget(self.hero, 1)
        self.hero_name = QLabel("…")
        self.hero_name.setObjectName("heroName")
        self.hero_name.setAlignment(Qt.AlignCenter)
        panel.body.addWidget(self.hero_name)
        self.hero_caption = QLabel("正在读取角色列表")
        self.hero_caption.setObjectName("heroCaption")
        self.hero_caption.setAlignment(Qt.AlignCenter)
        panel.body.addWidget(self.hero_caption)
        self.cards_row = QHBoxLayout()
        self.cards_row.setSpacing(8)
        panel.body.addLayout(self.cards_row)
        self.cards_placeholder = QLabel("连接后端后，这里显示 /api/voices 返回的角色。")
        self.cards_placeholder.setObjectName("muted")
        self.cards_placeholder.setWordWrap(True)
        self.cards_placeholder.setAlignment(Qt.AlignCenter)
        self.cards_placeholder.setMinimumHeight(120)
        self.cards_row.addWidget(self.cards_placeholder)
        self.original_button = QPushButton("原声示例（未变声）")
        self.original_button.setObjectName("ghost")
        self.original_button.setIconSize(QSize(12, 12))
        self.original_button.setIcon(make_icon("play", theme.SKY, 12))
        self.original_button.setToolTip("播放 assets/previews/original.wav，三位角色的示例都由这句话转换而来")
        self.original_button.setEnabled((PREVIEWS / "original.wav").is_file())
        panel.body.addWidget(self.original_button)
        return panel

    def _build_devices(self) -> QWidget:
        panel = Panel()
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        mic_label = QLabel("麦克风 · 录音和监听用")
        mic_label.setObjectName("fieldLabel")
        out_label = QLabel("输出设备 · 本机试听与监听")
        out_label.setObjectName("fieldLabel")
        self.mic_combo = ConsoleCombo()
        self.mic_combo.setAccessibleName("麦克风")
        self.out_combo = ConsoleCombo()
        self.out_combo.setAccessibleName("输出设备")
        self.rescan_button = QPushButton("刷新设备")
        self.rescan_button.setObjectName("ghost")
        self.rescan_button.setToolTip("插拔耳机或麦克风后点这里重新扫描")
        grid.addWidget(mic_label, 0, 0)
        grid.addWidget(out_label, 0, 1)
        grid.addWidget(self.mic_combo, 1, 0)
        grid.addWidget(self.out_combo, 1, 1)
        grid.addWidget(self.rescan_button, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        panel.body.addLayout(grid)
        return panel

    def _build_input(self) -> QWidget:
        panel = Panel("① 输入", "录音，或导入 WAV / FLAC / MP3 / OGG")
        row = QHBoxLayout()
        row.setSpacing(14)
        self.rec_button = RecButton()
        self.rec_button.setToolTip("开始录音，再点一次结束")
        row.addWidget(self.rec_button, 0, Qt.AlignVCenter)
        side = QVBoxLayout()
        side.setSpacing(6)
        self.rec_clock = QLabel("0:00.0")
        self.rec_clock.setObjectName("clock")
        side.addWidget(self.rec_clock)
        self.rec_meter = LevelMeter()
        side.addWidget(self.rec_meter)
        self.rec_hint = QLabel("点红色按钮开始录音")
        self.rec_hint.setObjectName("muted")
        self.rec_hint.setWordWrap(True)
        side.addWidget(self.rec_hint)
        row.addLayout(side, 1)
        panel.body.addLayout(row)
        panel.body.addStretch(1)
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.import_button = QPushButton("导入音频文件…")
        bottom.addWidget(self.import_button, 0, Qt.AlignVCenter)
        self.input_label = QLabel("当前输入：还没有")
        self.input_label.setObjectName("muted")
        self.input_label.setWordWrap(True)
        bottom.addWidget(self.input_label, 1)
        panel.body.addLayout(bottom)
        return panel

    def _build_mix(self) -> QWidget:
        panel = Panel("② 音色强度", "越高越接近角色")
        self.strength_value = QLabel("100%")
        self.strength_value.setObjectName("bigValue")
        panel.header.addWidget(self.strength_value)
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(0, 100)
        self.strength_slider.setSingleStep(5)
        self.strength_slider.setPageStep(10)
        self.strength_slider.setValue(100)
        self.strength_slider.setMinimumHeight(30)
        self.strength_slider.setAccessibleName("音色强度")
        panel.body.addWidget(self.strength_slider)
        ends = QHBoxLayout()
        left = QLabel("0% 原声")
        left.setObjectName("muted")
        right = QLabel("100% 角色")
        right.setObjectName("muted")
        ends.addWidget(left)
        ends.addStretch(1)
        ends.addWidget(right)
        panel.body.addLayout(ends)
        panel.body.addStretch(1)
        self.busy_bar = QProgressBar()
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setTextVisible(False)
        keep = self.busy_bar.sizePolicy()
        keep.setRetainSizeWhenHidden(True)
        self.busy_bar.setSizePolicy(keep)
        self.busy_bar.hide()
        panel.body.addWidget(self.busy_bar)
        self.convert_button = QPushButton("开始变声")
        self.convert_button.setObjectName("primary")
        self.convert_button.setMinimumHeight(44)
        panel.body.addWidget(self.convert_button)
        return panel

    def _build_audition(self) -> QWidget:
        panel = Panel("③ 试听与保存", "原声和结果可随时切换，播放位置保持不变")
        self.audition_panel = panel
        row = QHBoxLayout()
        row.setSpacing(12)
        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.seg_input = QPushButton("原声")
        self.seg_input.setObjectName("segLeft")
        self.seg_input.setCheckable(True)
        self.seg_input.setChecked(True)
        self.seg_result = QPushButton("变声结果")
        self.seg_result.setObjectName("segRight")
        self.seg_result.setCheckable(True)
        self.seg_group = QButtonGroup(self)
        self.seg_group.setExclusive(True)
        self.seg_group.addButton(self.seg_input)
        self.seg_group.addButton(self.seg_result)
        seg.addWidget(self.seg_input)
        seg.addWidget(self.seg_result)
        row.addLayout(seg)
        self.play_button = QPushButton("播放")
        self.play_button.setIconSize(QSize(14, 14))
        self.play_button.setMinimumWidth(92)
        row.addWidget(self.play_button)
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setMinimumHeight(30)
        self.seek_slider.setAccessibleName("播放进度")
        row.addWidget(self.seek_slider, 1)
        self.time_label = QLabel("0:00.0 / 0:00.0")
        self.time_label.setObjectName("muted")
        self.time_label.setMinimumWidth(104)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.time_label)
        panel.body.addLayout(row)
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        self.result_tag = QLabel()
        self.result_tag.setObjectName("resultTag")
        self.result_tag.setWordWrap(True)
        self.result_tag.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom.addWidget(self.result_tag, 1)
        self.save_button = QPushButton("另存为 WAV…")
        self.save_button.setMinimumHeight(36)
        bottom.addWidget(self.save_button, 0, Qt.AlignVCenter)
        panel.body.addLayout(bottom)
        return panel

    def _build_live(self) -> QWidget:
        panel = Panel("实时变声", "选择变声后的声音送到哪里")
        self.route_mode = ConsoleCombo()
        self.route_mode.addItem("Discord 通话", "discord")
        self.route_mode.addItem("本机监听", "local")
        panel.body.addWidget(self.route_mode)
        self.route_hint = QLabel()
        self.route_hint.setWordWrap(True)
        panel.body.addWidget(self.route_hint)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.live_switch = ToggleSwitch()
        self.live_switch.setAccessibleName("麦克风监听")
        row.addWidget(self.live_switch)
        self.live_title = QLabel("监听已关闭")
        self.live_title.setStyleSheet("font-size: 11.5pt; font-weight: 700;")
        self.live_title.setMinimumWidth(150)
        row.addWidget(self.live_title)
        tip = QFrame()
        tip.setObjectName("headphonesBox")
        tip.setStyleSheet(f"QFrame#headphonesBox {{ background: {theme.SUNFLOWER}; border-radius: 9px; }}"
                          f"QFrame#headphonesBox QLabel {{ color: {theme.INK}; font-size: 9pt; font-weight: 700;"
                          " background: transparent; }")
        tip_row = QHBoxLayout(tip)
        tip_row.setContentsMargins(10, 5, 12, 5)
        tip_row.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(make_icon("headphones", theme.INK, 16).pixmap(QSize(16, 16)))
        tip_row.addWidget(icon)
        tip_row.addWidget(QLabel("请戴耳机监听，外放会被麦克风收回去产生啸叫"))
        panel.header.addWidget(tip)
        in_label = QLabel("输入")
        in_label.setObjectName("fieldLabel")
        out_label = QLabel("输出")
        out_label.setObjectName("fieldLabel")
        self.live_in_meter = LevelMeter()
        self.live_out_meter = LevelMeter()
        row.addWidget(in_label)
        row.addWidget(self.live_in_meter, 1)
        row.addWidget(out_label)
        row.addWidget(self.live_out_meter, 1)
        panel.body.addLayout(row)
        self.live_status = QLabel("打开开关后开始实时变声。")
        self.live_status.setObjectName("muted")
        self.live_status.setWordWrap(True)
        panel.body.addWidget(self.live_status)
        return panel

    def _wire(self) -> None:
        b = self.bridge
        b.backend_progress.connect(self._on_backend_progress)
        b.backend_ready.connect(self._on_backend_ready)
        b.backend_failed.connect(self._on_backend_failed)
        b.voices_loaded.connect(self._on_voices_loaded)
        b.voices_failed.connect(self._on_voices_failed)
        b.health_result.connect(self._on_health)
        b.convert_done.connect(self._on_convert_done)
        b.convert_failed.connect(self._on_convert_failed)
        b.live_connected.connect(self._on_live_connected)
        b.live_stats.connect(self._on_live_stats)
        b.live_stopped.connect(self._on_live_stopped)

        self.reconnect_button.clicked.connect(self.connect_backend)
        self.original_button.clicked.connect(lambda: self.toggle_preview("original"))
        self.mic_combo.currentIndexChanged.connect(self._on_device_changed)
        self.out_combo.currentIndexChanged.connect(self._on_device_changed)
        self.route_mode.currentIndexChanged.connect(self._route_changed)
        self.rescan_button.clicked.connect(self.rescan_devices)
        self.rec_button.toggled.connect(self._on_rec_toggled)
        self.import_button.clicked.connect(self.import_dialog)
        self.strength_slider.valueChanged.connect(self._on_strength_changed)
        self.convert_button.clicked.connect(self.convert)
        self.seg_input.clicked.connect(lambda: self.set_ab("input"))
        self.seg_result.clicked.connect(lambda: self.set_ab("result"))
        self.play_button.clicked.connect(self.toggle_play)
        self.seek_slider.sliderReleased.connect(self._on_seek)
        self.save_button.clicked.connect(self.save_dialog)
        self.live_switch.toggled.connect(self._on_live_toggled)

    # ---- 通用 -----------------------------------------------------------
    def set_status(self, text: str, state: str = "") -> None:
        self.status_label.setText(text)
        set_state(self.status_label, state)

    def _voice_name(self, voice_id: str | None) -> str:
        return next((v["name"] for v in self.voices if v["id"] == voice_id), voice_id or "")

    def current_key(self) -> tuple | None:
        if self.input is None or self.voice_id is None:
            return None
        return (self.input.serial, self.voice_id, self.strength_pct)

    def current_result(self) -> ResultClip | None:
        key = self.current_key()
        return self.results.get(key) if key else None

    @staticmethod
    def _device(combo) -> audio.Device | None:
        return combo.currentData()

    def _refresh(self) -> None:
        """按当前状态统一设置各控件是否可用，以及结果与当前设置的对应关系。"""
        result = self.current_result()
        recording = self.recorder is not None
        live_on = self.live is not None
        converting = self.converting_key is not None
        has_mic = self._device(self.mic_combo) is not None
        has_out = self._device(self.out_combo) is not None

        self.rec_button.setEnabled(recording or (has_mic and not live_on))
        self.rec_button.setToolTip("开始录音，再点一次结束" if has_mic and not live_on else
                                   "监听占用着麦克风，先关闭监听" if live_on else "没有找到麦克风")
        self.import_button.setEnabled(not recording)
        self.mic_combo.setEnabled(has_mic and not recording)
        self.out_combo.setEnabled(has_out)
        self.rescan_button.setEnabled(not recording and not live_on)
        if not recording:
            self.rec_hint.setText("点红色按钮开始录音" if has_mic else "没有找到麦克风，可以导入音频文件")

        if self.input is None:
            self.input_label.setText("当前输入：还没有")
        else:
            clip = self.input
            self.input_label.setText(f"当前输入：{clip.label} · {clip.seconds:.2f} 秒 · {clip.rate} Hz")

        can_convert = (self.backend_ok and self.input is not None and self.voice_id is not None
                       and not converting and not live_on and not recording)
        self.convert_button.setEnabled(can_convert)
        self.convert_button.setText("变声中…" if converting else "开始变声")
        self.convert_button.setToolTip(
            "" if can_convert else
            "监听占用着同一个引擎，关闭监听后才能转换文件" if live_on else
            "正在转换" if converting else
            "后端未连接" if not self.backend_ok else
            "先结束录音" if recording else
            "先录音或导入一段音频" if self.input is None else "先选择角色")
        self.busy_bar.setVisible(converting)

        if self.ab == "result" and result is None:
            if self.playing_tag is not None and self.playing_tag[0] == "result":
                self.stop_playback()
            self.ab = "input"
        self.seg_input.setChecked(self.ab == "input")
        self.seg_result.setChecked(self.ab == "result")
        self.seg_input.setEnabled(self.input is not None)
        self.seg_result.setEnabled(result is not None)
        self.seg_result.setToolTip("" if result is not None else "当前输入、角色和强度还没有对应的结果")
        playing_ab = self.playing_tag is not None and self.playing_tag[0] in ("input", "result")
        self.play_button.setEnabled(playing_ab or (has_out and self.input is not None))
        self.play_button.setText("停止" if playing_ab else "播放")
        self.play_button.setIcon(make_icon("stop" if playing_ab else "play", theme.CREAM, 14))
        self.seek_slider.setEnabled(self.input is not None)
        self.save_button.setEnabled(result is not None)
        self.save_button.setToolTip("" if result is not None else "只有与当前输入、角色、强度对应的结果才能保存")
        self._update_result_tag(result)

        self.live_switch.setEnabled(live_on or (self.backend_ok and has_mic and has_out and not converting
                                                and not recording and self.voice_id is not None))
        self.live_switch.setToolTip(
            "" if self.live_switch.isEnabled() else
            "正在转换文件，完成后才能监听" if converting else
            "先结束录音" if recording else
            "后端未连接" if not self.backend_ok else
            "没有找到麦克风" if not has_mic else
            "没有找到输出设备" if not has_out else "先选择角色")
        if not live_on:
            self.live_title.setText("监听已关闭")
        self.hero.set_on_air(live_on)
        self.lamp.setText("ON AIR" if live_on else "REC" if recording else "STANDBY")
        set_state(self.lamp, "live" if live_on else "rec" if recording else "")

    def _update_result_tag(self, result: ResultClip | None) -> None:
        key = self.current_key()
        if result is not None:
            text = (f"当前结果：{result.voice_name} · 强度 {result.key[2]}% · 来源「{result.input_label}」"
                    f" · {len(result.samples) / result.rate:.2f} 秒，可试听和保存")
            state = "fresh"
        elif self.input is None:
            text, state = "先录音或导入一段音频，再点“开始变声”。", ""
        elif self.converting_key is not None and self.converting_key == key:
            text, state = f"正在生成：{self._voice_name(self.voice_id)} · 强度 {self.strength_pct}%…", ""
        else:
            others = [r for r in self.results.values() if r.key[0] == self.input.serial]
            if others:
                listed = "、".join(f"{r.voice_name} {r.key[2]}%" for r in sorted(others, key=lambda r: r.created))
                text = (f"当前设置（{self._voice_name(self.voice_id)} · 强度 {self.strength_pct}%）还没有结果。"
                        f"已有结果属于：{listed}。改回对应设置可继续试听和保存，或重新变声。")
                state = "stale"
            else:
                text, state = "这段输入还没有结果，点“开始变声”。", ""
        self.result_tag.setText(text)
        set_state(self.result_tag, state)

    # ---- 后端 -----------------------------------------------------------
    def connect_backend(self) -> None:
        if self._launcher is not None or self._closing:
            return
        self.notice.hide()
        self.backend_pill.setText("后端：检查中")
        set_state(self.backend_pill, "busy")
        self.reconnect_button.setEnabled(False)
        launcher = BackendLauncher(
            self.client,
            on_progress=lambda text: self._emit(self.bridge.backend_progress, text),
            on_ready=lambda health, started: self._emit(self.bridge.backend_ready, launcher, health, started),
            on_failed=lambda reason: self._emit(self.bridge.backend_failed, launcher, reason),
            autostart=self.config.autostart, script=self.config.script)
        self._launcher = launcher
        launcher.start()

    def _on_backend_progress(self, text: str) -> None:
        if self._launcher is not None:
            self.set_status(text)
            if "启动" in text:
                self.backend_pill.setText("后端：启动中")

    def _on_backend_ready(self, launcher, health: dict, started: bool) -> None:
        if launcher is not self._launcher:
            return
        self._launcher = None
        self.reconnect_button.setEnabled(True)
        if started:
            self.owned_backend = launcher.process
        self.max_seconds = float(health.get("max_seconds", self.max_seconds))
        self.max_bytes = int(health.get("max_bytes", self.max_bytes))
        self._set_backend(True)
        how = "由本程序启动（关闭窗口时一并停止）" if started else "复用已在运行的后端"
        self.set_status(f"已连接 {self.client.base_url} · {health.get('engine', '')} · {how}", "ok")
        self._load_voices()

    def _on_backend_failed(self, launcher, reason: str) -> None:
        if launcher is not self._launcher:
            return
        self._launcher = None
        self.reconnect_button.setEnabled(True)
        stop_process_tree(launcher.process)
        self._set_backend(False, reason)
        self.set_status("后端没有就绪，转换和监听暂时不可用。", "error")

    def _set_backend(self, ok: bool, reason: str = "") -> None:
        self.backend_ok = ok
        self._health_failures = 0
        self.backend_pill.setText("后端：已连接" if ok else "后端：未连接")
        set_state(self.backend_pill, "ok" if ok else "bad")
        if ok:
            self.notice.hide()
        else:
            self.notice.setText(f"后端未连接：{reason}\n点右上角“重新连接”会再检查一次，并在需要时启动 start-backend.cmd。")
            self.notice.show()
        self._refresh()

    def _poll_health(self) -> None:
        if self._health_inflight or self._launcher is not None or self._closing:
            return
        self._health_inflight = True

        def work():
            try:
                self.client.health()
                outcome = (True, "")
            except BackendError as exc:
                outcome = (False, str(exc))
            self._emit(self.bridge.health_result, *outcome)

        threading.Thread(target=work, daemon=True, name="health").start()

    def _on_health(self, ok: bool, message: str) -> None:
        self._health_inflight = False
        if self._launcher is not None:
            return
        if ok:
            self._health_failures = 0
            if not self.backend_ok:
                self._set_backend(True)
                self.set_status("后端恢复连接。", "ok")
                if not self.voices:
                    self._load_voices()
        else:
            self._health_failures += 1
            if self.backend_ok and self._health_failures >= 2:
                self._set_backend(False, message)
                self.set_status("与后端的连接断开了。", "error")

    def _load_voices(self) -> None:
        def work():
            try:
                voices = self.client.voices()
            except BackendError as exc:
                self._emit(self.bridge.voices_failed, str(exc))
                return
            self._emit(self.bridge.voices_loaded, voices)

        threading.Thread(target=work, daemon=True, name="voices").start()

    def _on_voices_failed(self, message: str) -> None:
        self.notice.setText(f"读取角色列表失败：{message}")
        self.notice.show()
        self.set_status("读取角色列表失败。", "error")

    def _on_voices_loaded(self, voices: list) -> None:
        self.voices = voices
        while self.cards_row.count():
            item = self.cards_row.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
                item.widget().deleteLater()
        self.cards = {}
        for voice in voices:
            style = theme.voice_style(voice["id"])
            pixmap = self._avatar if style.art == "avatar" else None
            card = VoiceCard(voice["id"], voice["name"], pixmap, (PREVIEWS / f"{voice['id']}.wav").is_file())
            card.chosen.connect(self.select_voice)
            card.preview_requested.connect(self.toggle_preview)
            self.cards_row.addWidget(card, 1)
            self.cards[voice["id"]] = card
        ids = [v["id"] for v in voices]
        if not ids:
            self._on_voices_failed("后端返回了空的角色列表。")
            return
        target = self.voice_id if self.voice_id in ids else "taffy" if "taffy" in ids else ids[0]
        self.voice_id = None
        self.select_voice(target)

    # ---- 角色 -----------------------------------------------------------
    def _show_voice(self, voice_id: str | None) -> None:
        style = theme.voice_style(voice_id or "taffy")
        self.hero.set_voice(style, self._avatar if style.art == "avatar" else None)
        if voice_id is None:
            self.hero_name.setText("…")
            self.hero_caption.setText("正在读取角色列表")
        else:
            self.hero_name.setText(self._voice_name(voice_id))
            self.hero_caption.setText(f"{voice_id.upper()} · 当前声线")
        self.hero_caption.setStyleSheet(f"color: {style.color};")
        for card_id, card in self.cards.items():
            card.set_active(card_id == voice_id)

    def select_voice(self, voice_id: str) -> None:
        if voice_id == self.voice_id or voice_id not in self.cards:
            return
        self.voice_id = voice_id
        self._show_voice(voice_id)
        self._refresh()
        if self.live is not None:
            self._restart_live()

    def _on_strength_changed(self, value: int) -> None:
        self.strength_pct = int(value)
        self.strength_value.setText(f"{value}%")
        self._refresh()
        if self.live is not None:
            self._strength_timer.start()

    # ---- 设备 -----------------------------------------------------------
    def _populate_devices(self, announce: bool = True) -> None:
        counts = []
        for combo, kind, empty in ((self.mic_combo, "input", "未找到麦克风"),
                                   (self.out_combo, "output", "未找到输出设备")):
            previous = combo.currentData().name if combo.currentData() is not None else None
            try:
                devices = audio.list_devices(kind)
            except audio.AudioDeviceError as exc:
                devices = []
                self.set_status(str(exc), "error")
            combo.blockSignals(True)
            combo.clear()
            for device in devices:
                combo.addItem(device.name + ("（默认）" if device.is_default else ""), device)
                combo.setItemData(combo.count() - 1,
                                  f"{device.name}\n{device.hostapi} · {device.rate} Hz · {device.channels} 声道",
                                  Qt.ToolTipRole)
            if not devices:
                combo.addItem(empty, None)
            index = next((i for i in range(combo.count())
                          if combo.itemData(i) is not None and combo.itemData(i).name == previous), 0)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)
            combo.setToolTip(combo.itemData(combo.currentIndex(), Qt.ToolTipRole) or empty)
            counts.append(len(devices))
        def available(combo):
            return [combo.itemData(i) for i in range(combo.count()) if combo.itemData(i)]
        self.discord_pair = audio.discord_pair(available(self.mic_combo), available(self.out_combo))
        self._route_changed()
        if announce:
            self.set_status(f"设备列表已刷新：{counts[0]} 个麦克风，{counts[1]} 个输出设备。")

    def _route_changed(self):
        if self.route_mode.currentData() == "discord":
            pair = self.discord_pair
            hint = (f"Discord → 语音与视频 → 输入设备：{pair[1].name}。通话输出仍选耳机。"
                    if pair else "未发现虚拟麦克风。安装 VB-CABLE 后刷新设备，或切换至本机监听。")
        else:
            hint = "变声通过所选输出设备播放。要让朋友听见，请选择 Discord 通话。"
        self.route_hint.setText(hint)
        if self.live is not None:
            self._restart_live()

    def rescan_devices(self) -> None:
        if self.recorder is not None or self.live is not None:
            return
        self.stop_playback()
        try:
            audio.rescan()
        except audio.AudioDeviceError as exc:
            self.set_status(str(exc), "error")
            return
        self._populate_devices()
        self._refresh()

    def _on_device_changed(self) -> None:
        for combo in (self.mic_combo, self.out_combo):
            combo.setToolTip(combo.itemData(combo.currentIndex(), Qt.ToolTipRole) or "")
        self._refresh()
        if self.live is not None:
            self._restart_live()

    # ---- 输入：录音与导入 -------------------------------------------------
    def _on_rec_toggled(self, checked: bool) -> None:
        if checked and self.recorder is None:
            self._start_recording()
        elif not checked and self.recorder is not None:
            self._stop_recording()

    def _start_recording(self) -> None:
        device = self._device(self.mic_combo)
        try:
            if device is None:
                raise audio.AudioDeviceError("没有找到麦克风，无法录音。")
            self.stop_playback()
            recorder = audio.Recorder(device, self.max_seconds)
            recorder.start()
        except audio.AudioDeviceError as exc:
            self.rec_button.setChecked(False)
            self.set_status(str(exc), "error")
            self._refresh()
            return
        self.recorder = recorder
        self._rec_started = time.monotonic()
        self.rec_hint.setText(f"正在录：{device.name}")
        self.set_status(f"正在用“{device.name}”录音，最长 {self.max_seconds:g} 秒。")
        self._refresh()

    def _stop_recording(self, note: str = "", lost: bool = False) -> None:
        recorder, self.recorder = self.recorder, None
        if recorder is None:
            return
        samples = recorder.stop()
        self.rec_button.setChecked(False)
        self.rec_meter.reset()
        seconds = len(samples) / recorder.rate
        self.rec_clock.setText(_clock(seconds if seconds >= audio.MIN_SECONDS else 0.0))
        if seconds < audio.MIN_SECONDS:
            self.set_status(f"{note}录音只有 {seconds:.2f} 秒，至少需要 {audio.MIN_SECONDS} 秒，没有替换当前输入。", "error")
            self._refresh()
            return
        self._set_input(f"录音 {time.strftime('%H:%M:%S')}", audio.encode_wav(samples, recorder.rate),
                        "audio/wav", samples, recorder.rate)
        if float(np.max(np.abs(samples))) < 0.003:
            self.set_status(f"{note}录好了 {seconds:.1f} 秒，但几乎没有声音，请检查“{recorder.device.name}”是否有信号。",
                            "error")
        else:
            self.set_status(f"{note}录好了 {seconds:.1f} 秒。", "error" if lost else "ok")

    def import_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入音频", self._last_dir, "音频文件 (*.wav *.flac *.mp3 *.ogg);;所有文件 (*)")
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path) -> bool:
        path = Path(path)
        try:
            size = path.stat().st_size
            if size > self.max_bytes:
                raise audio.AudioFileError(
                    f"文件有 {size / 1048576:.1f} MiB，超过后端上限 {self.max_bytes / 1048576:g} MiB。")
            data = path.read_bytes()
            samples, rate = audio.probe_file(data, self.max_seconds)
        except OSError as exc:
            self.set_status(f"无法读取 {path.name}：{exc}", "error")
            return False
        except audio.AudioFileError as exc:
            self.set_status(f"{path.name}：{exc}", "error")
            return False
        self._last_dir = str(path.parent)
        self._set_input(path.name, data, CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"),
                        samples, rate)
        self.set_status(f"已导入 {path.name}（{len(samples) / rate:.2f} 秒）。", "ok")
        return True

    def _set_input(self, label: str, data: bytes, content_type: str, samples: np.ndarray, rate: int) -> None:
        """换输入：旧输入的结果全部作废，避免把旧录音的结果当成新结果。"""
        if self.playing_tag is not None and self.playing_tag[0] in ("input", "result"):
            self.stop_playback()
        self._serial += 1
        self.input = InputClip(self._serial, label, data, content_type, samples, rate)
        self.results = {}
        self.ab = "input"
        self.seek_slider.setValue(0)
        self.time_label.setText(f"0:00.0 / {_clock(self.input.seconds)}")
        self._refresh()

    # ---- 转换 -----------------------------------------------------------
    def convert(self) -> None:
        key = self.current_key()
        if key is None or self.converting_key is not None or self.live is not None or not self.backend_ok:
            return
        clip, voice_id, strength = self.input, self.voice_id, self.strength_pct / 100
        self.converting_key = key
        self._convert_started = time.monotonic()
        self.set_status(f"正在把「{clip.label}」变成 {self._voice_name(voice_id)}（强度 {self.strength_pct}%）…")
        self._refresh()

        def work():
            started = time.perf_counter()
            try:
                wav = self.client.convert(clip.data, clip.content_type, voice_id, strength)
            except BackendError as exc:
                self._emit(self.bridge.convert_failed, key, str(exc))
                return
            self._emit(self.bridge.convert_done, key, wav, time.perf_counter() - started)

        threading.Thread(target=work, daemon=True, name="convert").start()

    @staticmethod
    def _emit(signal, *args) -> None:
        try:
            signal.emit(*args)
        except RuntimeError:
            pass  # 窗口已销毁

    def _on_convert_done(self, key: tuple, wav: bytes, elapsed: float) -> None:
        self.converting_key = None
        if self.input is None or key[0] != self.input.serial:
            self.set_status("转换完成时输入已经更换，旧输入的结果已丢弃。")
            self._refresh()
            return
        try:
            samples, rate = sf.read(io.BytesIO(wav), dtype="float32", always_2d=True)
        except Exception as exc:
            self.set_status(f"后端返回的结果无法解码：{exc}", "error")
            self._refresh()
            return
        result = ResultClip(key, wav, samples.mean(axis=1), rate, self._voice_name(key[1]),
                            self.input.label, elapsed)
        self.results[key] = result
        while len(self.results) > MAX_RESULTS:
            oldest = min(self.results.values(), key=lambda r: r.created)
            del self.results[oldest.key]
        described = f"{result.voice_name} · 强度 {key[2]}%"
        if key == self.current_key():
            was_playing = self.playing_tag is not None and self.playing_tag[0] == "input"
            self.ab = "result"
            if was_playing:
                self.stop_playback()
            self.set_status(f"变声完成：{described}，用时 {elapsed:.1f} 秒。可以试听并另存为 WAV。", "ok")
        else:
            self.set_status(f"变声完成：{described}（用时 {elapsed:.1f} 秒）。当前设置已经改过，改回这组设置即可试听和保存。")
        self._refresh()

    def _on_convert_failed(self, key: tuple, message: str) -> None:
        self.converting_key = None
        self.set_status(f"转换失败：{message}", "error")
        self._refresh()

    # ---- 试听 -----------------------------------------------------------
    def _play(self, tag: tuple, samples: np.ndarray, rate: int, start: float = 0.0) -> bool:
        device = self._device(self.out_combo)
        try:
            if device is None:
                raise audio.AudioDeviceError("没有找到输出设备，无法播放。")
            self.player.play(samples, rate, device, start)
        except audio.AudioDeviceError as exc:
            self.stop_playback()
            self.set_status(str(exc), "error")
            return False
        self.playing_tag = tag
        self._sync_preview_buttons()
        self._refresh()
        return True

    def stop_playback(self) -> None:
        was_ab = self.playing_tag is not None and self.playing_tag[0] in ("input", "result")
        self.player.stop()
        self.playing_tag = None
        self._sync_preview_buttons()
        if was_ab:
            self.seek_slider.setValue(0)
            self._show_time(0.0)
            self._refresh()

    def _sync_preview_buttons(self) -> None:
        current = self.playing_tag[1] if self.playing_tag is not None and self.playing_tag[0] == "preview" else None
        for voice_id, card in self.cards.items():
            card.set_previewing(voice_id == current)
        playing_original = current == "original"
        self.original_button.setText("停止原声示例" if playing_original else "原声示例（未变声）")
        self.original_button.setIcon(make_icon("stop" if playing_original else "play", theme.SKY, 12))

    def toggle_preview(self, name: str) -> None:
        """立即播放 assets/previews 下的示例；再点一次停止。"""
        if self.playing_tag == ("preview", name):
            self.stop_playback()
            return
        path = PREVIEWS / f"{name}.wav"
        try:
            samples, rate = sf.read(str(path), dtype="float32", always_2d=True)
        except Exception as exc:
            self.set_status(f"无法读取示例 {path.name}：{exc}", "error")
            return
        self.stop_playback()
        label = "原声示例" if name == "original" else f"{self._voice_name(name)} 的示例"
        if self._play(("preview", name), samples.mean(axis=1), rate):
            self.set_status(f"正在播放{label}（{path.name}）→ {self._device(self.out_combo).name}")

    def _ab_clip(self, which: str):
        if which == "result":
            result = self.current_result()
            return (result.samples, result.rate) if result is not None else None
        return (self.input.samples, self.input.rate) if self.input is not None else None

    def _ab_duration(self) -> float:
        clip = self._ab_clip(self.ab)
        return len(clip[0]) / clip[1] if clip is not None else 0.0

    def _show_time(self, position: float) -> None:
        self.time_label.setText(f"{_clock(position)} / {_clock(self._ab_duration())}")

    def set_ab(self, which: str) -> None:
        """切换原声 / 结果。播放中切换时从同一时间点接着播。"""
        if which == "result" and self.current_result() is None:
            which = "input"
        playing = self.playing_tag is not None and self.playing_tag[0] in ("input", "result")
        position = self.player.position if playing else self.seek_slider.value() / 1000 * self._ab_duration()
        self.ab = which
        if playing:
            self.player.stop()
            self.playing_tag = None
            clip = self._ab_clip(which)
            duration = len(clip[0]) / clip[1]
            self._play((which, self.current_key()), clip[0], clip[1], position if position < duration - 0.05 else 0.0)
        else:
            self._refresh()
        self._show_time(position if playing else self.seek_slider.value() / 1000 * self._ab_duration())

    def toggle_play(self) -> None:
        if self.playing_tag is not None and self.playing_tag[0] in ("input", "result"):
            self.stop_playback()
            return
        clip = self._ab_clip(self.ab)
        if clip is None:
            return
        self.stop_playback()
        duration = len(clip[0]) / clip[1]
        fraction = self.seek_slider.value() / 1000
        start = fraction * duration if fraction < 0.98 else 0.0
        if self._play((self.ab, self.current_key()), clip[0], clip[1], start):
            what = "变声结果" if self.ab == "result" else "原声"
            self.set_status(f"正在播放{what} → {self._device(self.out_combo).name}")

    def _on_seek(self) -> None:
        duration = self._ab_duration()
        position = self.seek_slider.value() / 1000 * duration
        if self.playing_tag is not None and self.playing_tag[0] in ("input", "result"):
            self.player.seek(self.seek_slider.value() / 1000 * self.player.duration)
        self._show_time(position)

    # ---- 保存 -----------------------------------------------------------
    def save_dialog(self) -> None:
        result = self.current_result()
        if result is None:
            return
        stem = Path(result.input_label).stem.replace(":", "-").replace(" ", "_") or "voice"
        default = str(Path(self._last_dir) / f"{stem}_{result.key[1]}_{result.key[2]}.wav")
        path, _ = QFileDialog.getSaveFileName(self, "另存为 WAV", default, "WAV 音频 (*.wav)")
        if path:
            self.save_result(Path(path))

    def save_result(self, path: Path) -> bool:
        """只保存与当前输入、角色、强度对应的结果，写出后端返回的原始 WAV 字节。"""
        result = self.current_result()
        if result is None:
            self.set_status("当前输入、角色和强度没有对应的结果，没有保存。", "error")
            return False
        path = Path(path)
        if path.suffix.lower() != ".wav":
            path = path.with_name(path.name + ".wav")
        try:
            path.write_bytes(result.wav)
        except OSError as exc:
            self.set_status(f"保存失败：{exc}", "error")
            return False
        self._last_dir = str(path.parent)
        self.set_status(f"已保存 {path}（{result.voice_name} · 强度 {result.key[2]}% · 来源「{result.input_label}」）", "ok")
        return True

    # ---- 麦克风监听 -------------------------------------------------------
    def _on_live_toggled(self, checked: bool) -> None:
        if checked and self.live is None:
            self._start_live()
        elif checked:
            self._live_restart = True  # 上一个会话还在收尾，结束后接着开
        elif self.live is not None:
            self._live_restart = False
            self.live.request_stop()
            self.live_title.setText("正在停止…")

    def _open_live_devices(self):
        """在界面线程打开并启动采集和播放流，之后交给工作线程。"""
        mic_device, out_device = self._device(self.mic_combo), self._device(self.out_combo)
        receiver = None
        if self.route_mode.currentData() == "discord":
            if not self.discord_pair:
                raise audio.AudioDeviceError("未找到 Steam 或 VB-CABLE 的成对虚拟音频设备。")
            out_device, receiver = self.discord_pair
            if mic_device == receiver:
                raise audio.AudioDeviceError("采集设备请选择你说话用的麦克风，以免形成回路。")
        if mic_device is None:
            raise audio.AudioDeviceError("没有找到麦克风，无法监听。")
        if out_device is None:
            raise audio.AudioDeviceError("没有找到输出设备，无法监听。")
        mic = audio.MicStream(mic_device)
        try:
            speaker = audio.SpeakerStream(out_device, slack_seconds=0.24, receiver=receiver)
        except audio.AudioDeviceError:
            mic.close()
            raise
        try:
            mic.start()
            speaker.start()
        except audio.AudioDeviceError:
            mic.close()
            speaker.close()
            raise
        return mic, speaker

    def _start_live(self) -> None:
        if not self.backend_ok or self.voice_id is None or self.converting_key is not None:
            self.live_switch.setChecked(False)
            return
        try:
            mic, speaker = self._open_live_devices()
        except audio.AudioDeviceError as exc:
            self.live_switch.setChecked(False)
            self.live_status.setText(f"监听没有打开：{exc}")
            self.set_status(str(exc), "error")
            self._refresh()
            return
        url = self.client.live_url(self.voice_id, self.strength_pct / 100)
        monitor = LiveMonitor(
            url, mic, speaker,
            on_connected=lambda hello: self._emit(self.bridge.live_connected, monitor, hello),
            on_stats=lambda stats: self._emit(self.bridge.live_stats, monitor, stats),
            on_stopped=lambda kind, message: self._emit(self.bridge.live_stopped, monitor, kind, message))
        monitor.label = f"{self._voice_name(self.voice_id)} · 强度 {self.strength_pct}%"
        self.live = monitor
        self._live_stats = {}
        self.live_title.setText("正在连接…")
        self.live_status.setText(f"麦克风：{mic.name} → 输出：{speaker.name}")
        monitor.start()
        self._refresh()

    def _restart_live(self) -> None:
        """切换角色、强度或设备时重新连接。"""
        if self.live is None or not self.live_switch.isChecked():
            return
        self._live_restart = True
        self.live.request_stop(abort=True)
        self.live_title.setText("正在重新连接…")

    def _on_live_connected(self, monitor, hello: dict) -> None:
        if monitor is not self.live:
            return
        mode = self.route_mode.currentText()
        self.live_title.setText(f"{mode}中 · {monitor.label}")
        self.set_status(f"监听已连接：{hello['sample_rate']} Hz，每帧 {hello['frame_samples']} 个样本。请戴耳机。", "ok")

    def _on_live_stats(self, monitor, stats: dict) -> None:
        if monitor is not self.live:
            return
        self._live_stats = stats
        speaker = monitor.speaker
        # 凑满一帧的等待 + 推理往返 + 播放余量 + 服务端保留的 1,024 个交叉淡化样本 + 输出设备缓冲
        frame_ms = monitor.hello["frame_samples"] / monitor.hello["sample_rate"] * 1000
        overlap_ms = monitor.hello.get("lookahead_samples", 1024) / monitor.hello["sample_rate"] * 1000
        delay = (frame_ms + stats["avg_ms"] + getattr(speaker, "slack_seconds", 0) * 1000 + overlap_ms
                 + getattr(speaker, "latency", 0) * 1000) / 1000
        self.live_status.setText(
            f"麦克风：{monitor.mic.name} → 输出：{speaker.name}\n"
            f"已送 {stats['frames']} 帧 · 每帧往返 {stats['avg_ms']:.0f} 毫秒 · 估算延迟约 {delay:.1f} 秒"
            f" · 丢弃输入 {stats['mic_dropped']} 块 · 播放断流 {stats['underruns']} 次")

    def _on_live_stopped(self, monitor, kind: str, message: str) -> None:
        if monitor is not self.live:
            return
        self.live = None
        restart, self._live_restart = self._live_restart, False
        self.live_in_meter.reset()
        self.live_out_meter.reset()
        if restart and kind == "user" and self.live_switch.isChecked() and not self._closing:
            self._start_live()
            return
        self.live_switch.setChecked(False)
        if kind == "error":
            self.live_status.setText(f"监听已停止：{message}")
            self.set_status(message, "error")
        else:
            self.live_status.setText("监听已关闭，麦克风和输出设备已释放。")
            self.set_status("监听已关闭。")
        self._refresh()

    # ---- 定时刷新 ---------------------------------------------------------
    def _tick(self) -> None:
        if self.playing_tag is not None:
            if self.player.playing:
                if self.playing_tag[0] in ("input", "result") and not self.seek_slider.isSliderDown():
                    duration = self.player.duration or 1.0
                    self.seek_slider.setValue(int(self.player.position / duration * 1000))
                    self._show_time(self.player.position)
            else:
                self.stop_playback()
        if self.recorder is not None:
            self.rec_meter.set_peak(self.recorder.level)
            self.rec_clock.setText(_clock(self.recorder.seconds))
            if self.recorder.full:
                self._stop_recording(f"已到 {self.max_seconds:g} 秒上限，自动停止。")
            elif not self.recorder.active:
                self._stop_recording("麦克风已断开，录音提前结束。", lost=True)
        if self.live is not None:
            self.live_in_meter.set_peak(self.live.mic.level)
            self.live_out_meter.set_peak(getattr(self.live.speaker, "level", 0.0))
        if self.converting_key is not None:
            self.convert_button.setText(f"变声中… {time.monotonic() - self._convert_started:.0f} 秒")

    # ---- 退出 -----------------------------------------------------------
    def closeEvent(self, event) -> None:
        """关闭窗口：停止播放和录音，结束监听并释放设备，停掉由本程序启动的后端。"""
        self._closing = True
        self._tick_timer.stop()
        self._health_timer.stop()
        self._strength_timer.stop()
        self.player.stop()
        if self.recorder is not None:
            self.recorder.stop()
            self.recorder = None
        if self.live is not None:
            self.live.request_stop(abort=True)
            self.live.join(3.0)
        if self._launcher is not None:
            self._launcher.cancel()
            stop_process_tree(self._launcher.process)
        stop_process_tree(self.owned_backend)
        event.accept()
