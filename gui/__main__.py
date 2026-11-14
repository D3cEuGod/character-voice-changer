"""入口：python -m gui [--backend-url URL] [--no-autostart] [--backend-script PATH]"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from .backend import DEFAULT_URL, ROOT, START_SCRIPT

from .taskbar import set_process_app_id, set_window_relaunch

LOG_FILE = ROOT / ".run" / "gui.log"
_APPLICATION = None


def cleanup_qt_styles():
    """Release Qt's stylesheet proxies before widget wrappers are torn down."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet("")


def create_app(argv=None):
    """先创建 QApplication，再导入会加载 PortAudio 的模块（顺序反了会让 Qt 的原生文件对话框失效）。"""
    global _APPLICATION
    set_process_app_id()  # 要在创建任何窗口之前
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtWidgets import QApplication

    from . import theme

    # 125%、150% 等非整数缩放按系统比例原样渲染
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(list(argv or sys.argv[:1]))
    # Keep Qt alive while main() releases its window wrappers and Python runs
    # PortAudio's exit handlers. Destroying QApplication first can crash QtWidgets.
    _APPLICATION = app
    if not app.property("voiceQuitCleanupConnected"):
        app.aboutToQuit.connect(cleanup_qt_styles)
        app.setProperty("voiceQuitCleanupConnected", True)
    app.setApplicationName("角色变声器")
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    app.setStyleSheet(theme.STYLESHEET)
    return app


def _log_exception(kind, value, trace) -> None:
    text = "".join(traceback.format_exception(kind, value, trace))
    try:
        LOG_FILE.parent.mkdir(exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as log:
            log.write(text + "\n")
    except OSError:
        pass
    if sys.stderr is not None:
        sys.stderr.write(text)
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is not None:
            QMessageBox.critical(None, "角色变声器出错了", f"{value}\n\n详细信息已写入 {LOG_FILE}")
    except Exception:
        pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m gui", description="角色变声器桌面界面")
    parser.add_argument("--backend-url", default=os.environ.get("VOICE_GUI_BACKEND_URL", DEFAULT_URL),
                        help=f"后端地址，默认 {DEFAULT_URL}")
    parser.add_argument("--no-autostart", action="store_true", help="后端未运行时不自动启动")
    parser.add_argument("--backend-script", default=str(START_SCRIPT), help="启动后端用的脚本")
    parser.add_argument("--live-restart-packets", type=int, choices=(0, 3000, 5000), default=3000,
                        help="自动重开实时变声的包数，默认 3000；0 关闭自动刷新")
    parser.add_argument("--live-packet-ms", type=int, choices=(100,120), default=120,
                        help="VB-CABLE 包长；默认稳定档 120，100 为实验低延迟档")
    args = parser.parse_args(argv)

    sys.excepthook = _log_exception
    app = create_app()
    from .app import Config, MainWindow

    window = MainWindow(Config(args.backend_url, not args.no_autostart, Path(args.backend_script),
                               args.live_restart_packets, args.live_packet_ms))
    available = app.primaryScreen().availableGeometry()
    window.resize(min(1060, available.width() - 40), min(700, available.height() - 60))
    set_window_relaunch(int(window.winId()))  # 在窗口显示之前写入，任务栏按这些信息建立图标
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
