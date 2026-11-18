"""设置面板与首次引导。只在 QApplication 创建之后导入。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from . import __version__, audio, hotkey
from .backend import ROOT
from .settings import default_path
from .widgets import Card, ConsoleCombo, LevelMeter, divider, label, set_state

VB_CABLE_URL = "https://vb-audio.com/Cable/"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
LOG_DIR = ROOT / ".run"
RESTART_NAMES = {3000: "每 3,000 包自动刷新（推荐）", 5000: "每 5,000 包自动刷新", 0: "不自动刷新"}


def open_path(path: Path) -> None:
    """用系统的文件管理器打开文件夹或文件。"""
    if not path.suffix:
        path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  打开的是本程序自己的文件夹
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def _wrap(text: str, name: str = "body") -> QLabel:
    widget = label(text, name)
    widget.setWordWrap(True)
    widget.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
    widget.setOpenExternalLinks(True)
    return widget


class SettingsDialog(QDialog):
    """常用：快捷键、托盘。高级：自动刷新、低延迟档。帮助与关于。改动立即生效并保存。"""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.settings = window.settings
        self.setWindowTitle("设置")
        self.setMinimumWidth(520)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 14)
        outer.setSpacing(12)

        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        card.body.addWidget(label("常用", "heading"))
        card.body.addLayout(grid)

        self.hotkey_combo = ConsoleCombo()
        for name in hotkey.CHOICES:
            self.hotkey_combo.addItem(name or "不使用", name)
        index = self.hotkey_combo.findData(self.settings.hotkey)
        self.hotkey_combo.setCurrentIndex(index if index >= 0 else 0)
        self.hotkey_combo.setAccessibleName("开关变声的快捷键")
        grid.addWidget(label("开关变声的快捷键", "sectionLabel"), 0, 0)
        grid.addWidget(self.hotkey_combo, 0, 1)
        self.hotkey_note = _wrap("", "muted")
        grid.addWidget(self.hotkey_note, 1, 1)
        if window.hotkey is None or not hotkey.available:
            self.hotkey_combo.setEnabled(False)
            self.hotkey_note.setText("全局快捷键只在 Windows 上可用。")
        else:
            self._show_hotkey_state()

        self.tray_box = QCheckBox("关闭窗口时最小化到托盘，变声继续")
        self.tray_box.setChecked(self.settings.close_to_tray)
        self.tray_box.setEnabled(window.tray is not None)
        grid.addWidget(self.tray_box, 2, 0, 1, 2)
        grid.setColumnStretch(1, 1)
        outer.addWidget(card)

        advanced = Card()
        advanced.body.addWidget(label("高级", "heading"))
        rows = QGridLayout()
        rows.setHorizontalSpacing(14)
        rows.setVerticalSpacing(10)
        self.restart_combo = ConsoleCombo()
        for packets, name in RESTART_NAMES.items():
            self.restart_combo.addItem(name, packets)
        self.restart_combo.setCurrentIndex(max(0, self.restart_combo.findData(window.config.live_restart_packets)))
        self.restart_combo.setToolTip("长时间通话时定期重开一次实时变声，防止音质慢慢变差。重开时会有很短的停顿。")
        rows.addWidget(label("长时间通话", "sectionLabel"), 0, 0)
        rows.addWidget(self.restart_combo, 0, 1)
        self.fast_box = QCheckBox("低延迟实验档（100 ms 包，延迟更低，偶尔可能断续）")
        self.fast_box.setChecked(window.config.live_packet_ms == 100)
        self.fast_box.setToolTip("只影响 VB-CABLE。默认 120 ms 更稳定。下次开始变声时生效。")
        rows.addWidget(self.fast_box, 1, 0, 1, 2)
        rows.setColumnStretch(1, 1)
        advanced.body.addLayout(rows)
        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.guide_button = QPushButton("重新运行新手引导")
        self.settings_folder = QPushButton("打开设置文件夹")
        self.log_folder = QPushButton("打开日志文件夹")
        for button in (self.guide_button, self.settings_folder, self.log_folder):
            tools.addWidget(button)
        tools.addStretch(1)
        advanced.body.addLayout(tools)
        outer.addWidget(advanced)

        about = Card()
        about.body.addWidget(label(f"关于 · 角色变声器 v{__version__}", "heading"))
        about.body.addWidget(_wrap(
            "声音只在这台电脑上处理，不会上传到任何服务器。<br>"
            "请勿用变声冒充他人、骗取信任或从事违法活动。角色名称、形象和声线模型的权利归各自的权利人所有，"
            "仅供个人娱乐使用。<br>"
            f'开源组件与许可见 <a style="color:#E9739B" href="{QUrl.fromLocalFile(str(NOTICES)).toString()}">第三方声明</a>。', "muted"))
        outer.addWidget(about)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.done_button = QPushButton("完成")
        self.done_button.setObjectName("primary")
        self.done_button.setDefault(True)
        buttons.addWidget(self.done_button)
        outer.addLayout(buttons)

        self.hotkey_combo.currentIndexChanged.connect(self._hotkey_changed)
        self.tray_box.toggled.connect(self._tray_changed)
        self.restart_combo.currentIndexChanged.connect(self._advanced_changed)
        self.fast_box.toggled.connect(self._advanced_changed)
        self.guide_button.clicked.connect(self._guide)
        self.settings_folder.clicked.connect(lambda: open_path((self.settings.path or default_path()).parent))
        self.log_folder.clicked.connect(lambda: open_path(LOG_DIR))
        self.done_button.clicked.connect(self.accept)

    def _show_hotkey_state(self) -> None:
        error = self.window_.hotkey_error
        current = self.window_.hotkey_text()
        self.hotkey_note.setText(error or (f"在任何程序里按 {current} 都能开关变声，玩游戏时也有效。" if current
                                           else "不使用快捷键时，可以在托盘图标上右键开关变声。"))
        set_state(self.hotkey_note, "error" if error else "")

    def _hotkey_changed(self) -> None:
        name = self.hotkey_combo.currentData()
        self.window_.apply_hotkey(name)
        self.settings.hotkey = name
        self.settings.save()
        self._show_hotkey_state()

    def _tray_changed(self, checked: bool) -> None:
        self.settings.close_to_tray = checked
        self.settings.save()

    def _advanced_changed(self) -> None:
        config = self.window_.config
        config.live_restart_packets = self.restart_combo.currentData()
        config.live_packet_ms = 100 if self.fast_box.isChecked() else 120
        self.settings.live_restart_packets = config.live_restart_packets
        self.settings.live_packet_ms = config.live_packet_ms
        self.settings.save()

    def _guide(self) -> None:
        self.accept()
        QTimer.singleShot(0, self.window_.run_onboarding)


class OnboardingDialog(QDialog):
    """第一次打开时的三步引导：选麦克风并试音、连到语音软件、记住快捷键。"""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.setWindowTitle("欢迎使用角色变声器")
        self.setMinimumSize(560, 400)
        self.stream: audio.MicStream | None = None
        self.advisor = audio.MicAdvisor(window=2.0)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 14)
        outer.setSpacing(12)
        self.steps = label("", "sectionLabel")
        outer.addWidget(self.steps)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._mic_page())
        self.pages.addWidget(self._call_page())
        self.pages.addWidget(self._done_page())
        outer.addWidget(self.pages, 1)
        outer.addWidget(divider())
        row = QHBoxLayout()
        self.skip_button = QPushButton("跳过")
        self.skip_button.setObjectName("ghost")
        row.addWidget(self.skip_button)
        row.addStretch(1)
        self.back_button = QPushButton("上一步")
        self.next_button = QPushButton("下一步")
        self.next_button.setObjectName("primary")
        self.next_button.setDefault(True)
        row.addWidget(self.back_button)
        row.addWidget(self.next_button)
        outer.addLayout(row)

        self.skip_button.clicked.connect(self.reject)
        self.back_button.clicked.connect(lambda: self.go(self.pages.currentIndex() - 1))
        self.next_button.clicked.connect(self._next)
        self.mic_choice.currentIndexChanged.connect(self._open_mic)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self.finished.connect(self._close_mic)
        self.go(0)

    # ---- 页面 ----------------------------------------------------------------
    def _mic_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(label("第一步：选你说话用的麦克风", "heading"))
        layout.addWidget(_wrap("选好以后对着麦克风正常说几句话，看下面的电平条有没有跟着动。"))
        self.mic_choice = ConsoleCombo()
        main = self.window_.mic_combo
        receiver = self.window_.discord_pair[1] if self.window_.discord_pair else None
        for i in range(main.count()):
            device = main.itemData(i)
            if device is not None and (receiver is None or device.name != receiver.name):
                self.mic_choice.addItem(main.itemText(i), device)
        if self.mic_choice.count() == 0:
            self.mic_choice.addItem("未找到麦克风", None)
        current = main.currentData()
        if current is not None:
            index = next((i for i in range(self.mic_choice.count())
                          if self.mic_choice.itemData(i) is not None
                          and self.mic_choice.itemData(i).name == current.name), 0)
            self.mic_choice.setCurrentIndex(index)
        layout.addWidget(self.mic_choice)
        self.mic_meter = LevelMeter()
        layout.addWidget(self.mic_meter)
        self.mic_result = _wrap("正在打开麦克风…", "muted")
        layout.addWidget(self.mic_result)
        layout.addStretch(1)
        return page

    def _call_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(label("第二步：连到 Discord 等语音软件", "heading"))
        pair = self.window_.discord_pair
        if pair:
            text = (f"已找到虚拟麦克风 <b>{pair[1].name}</b>。<br><br>"
                    "在 Discord 里打开 <b>用户设置 → 语音与视频</b>：<br>"
                    f"1. 输入设备选 <b>{pair[1].name}</b>；输出设备继续用你的耳机。<br>"
                    "2. 输入配置文件选 <b>Studio</b>（关闭降噪），否则 Discord 会把变声后的声音当成噪音切掉。<br><br>"
                    "QQ、YY、游戏语音同理，把麦克风选成上面这个设备即可。")
        else:
            text = ("没有找到虚拟麦克风。想让 Discord 等语音软件听到变声，需要先安装免费的 "
                    f'<a style="color:#E9739B" href="{VB_CABLE_URL}">VB-CABLE</a>（需要管理员权限，装完重启电脑）。<br><br>'
                    "现在也可以先打开“耳返”，从耳机里听自己的变声效果。")
        layout.addWidget(_wrap(text))
        if not pair:
            self.vb_button = QPushButton("打开 VB-CABLE 官网")
            self.vb_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(VB_CABLE_URL)))
            layout.addWidget(self.vb_button, 0, Qt.AlignLeft)
        layout.addStretch(1)
        return page

    def _done_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(label("准备好了", "heading"))
        key = self.window_.hotkey_text()
        tips = ["选好角色，点中间的大圆键就开始变声，再点一次停止。"]
        if key:
            tips.append(f"在任何程序里按 <b>{key}</b> 都能开关变声，玩游戏时也有效。")
        if self.window_.tray is not None:
            tips.append("关掉窗口后变声器还在托盘里运行，右键托盘图标可以开关变声或退出。")
        tips.append("声音太尖可以把“音高”改成“模型默认”；咬字不清可以试试“通话清晰”。")
        layout.addWidget(_wrap("<br><br>".join(tips)))
        layout.addStretch(1)
        return page

    # ---- 流程 ----------------------------------------------------------------
    def go(self, index: int) -> None:
        index = max(0, min(self.pages.count() - 1, index))
        self.pages.setCurrentIndex(index)
        self.steps.setText(f"新手引导 · {index + 1} / {self.pages.count()}")
        self.back_button.setEnabled(index > 0)
        self.next_button.setText("开始使用" if index == self.pages.count() - 1 else "下一步")
        if index == 0:
            self._open_mic()
        else:
            self._close_mic()

    def _next(self) -> None:
        if self.pages.currentIndex() == 0:
            self._apply_mic()
        if self.pages.currentIndex() == self.pages.count() - 1:
            self.accept()
        else:
            self.go(self.pages.currentIndex() + 1)

    def _apply_mic(self) -> None:
        device = self.mic_choice.currentData()
        main = self.window_.mic_combo
        if device is None:
            return
        for i in range(main.count()):
            if main.itemData(i) is not None and main.itemData(i).name == device.name:
                main.setCurrentIndex(i)
                return

    def _open_mic(self) -> None:
        self._close_mic()
        self.advisor.reset()
        device = self.mic_choice.currentData()
        if device is None:
            self.mic_result.setText("没有找到麦克风。插上麦克风后，在主界面点“刷新”。")
            return
        try:
            self.stream = audio.MicStream(device)
            self.stream.start()
        except audio.AudioDeviceError as exc:
            self.stream = None
            self.mic_result.setText(str(exc))
            set_state(self.mic_result, "error")
            return
        self.mic_result.setText("请对着麦克风说几句话…")
        set_state(self.mic_result, "")
        self._timer.start()

    def _close_mic(self, *_) -> None:
        self._timer.stop()
        stream, self.stream = self.stream, None
        if stream is not None:
            stream.close()
        self.mic_meter.reset()

    def _tick(self) -> None:
        stream = self.stream
        if stream is None:
            return
        while not stream.blocks.empty():  # 只看电平，不留音频
            try:
                stream.blocks.get_nowait()
            except Exception:
                break
        self.mic_meter.set_peak(stream.level)
        state, text = self.advisor.feed(stream.level)
        if state == "ok":
            self.mic_result.setText("声音正常，可以下一步了。")
            set_state(self.mic_result, "ok")
        elif state:
            self.mic_result.setText(text)
            set_state(self.mic_result, "warn")

