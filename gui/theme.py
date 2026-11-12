"""配色与样式表。颜色取自 assets/taffy-avatar.jpg：樱粉头发、海军蓝贝雷帽、向日葵黄。"""
from dataclasses import dataclass

BACKGROUND = "#0E1530"
CARD = "#161F42"
FIELD = "#0F1736"
RAISED = "#212D5C"
LINE = "#2C3B73"
NAVY_900 = BACKGROUND
NAVY_700 = RAISED
NAVY_600 = LINE
SAKURA = "#F7B9CB"
SAKURA_DEEP = "#EC86A6"
SUNFLOWER = "#F8C537"
SUNFLOWER_DEEP = "#E3A012"
SKY = "#7CC4F2"
CREAM = "#FFF7EC"
MUTED = "#98A4CC"
DIM = "#5F6A93"
DANGER = "#FF5C7A"
OK = "#7BE0A6"
INK = "#2A1E00"

FONT_FAMILY = '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif'


@dataclass(frozen=True)
class VoiceStyle:
    color: str      # 角色色
    accent: str     # 高亮色
    art: str        # 没有头像文件时的图案：mic | guitar | note
    avatar: str     # assets/ 下的头像文件名，可以为空


# 角色名字来自 GET /api/voices；这里只为已知 id 配美术。未知 id 用通用音符图案。
VOICE_STYLES = {
    "taffy": VoiceStyle(SAKURA, SUNFLOWER, "note", "taffy-avatar.jpg"),
    "tomori": VoiceStyle("#77BBDD", "#C8E8F7", "mic", "tomori-avatar.png"),
    "anon": VoiceStyle("#FF8899", "#FFD0D8", "guitar", "anon-avatar.png"),
}
FALLBACK_STYLES = (
    VoiceStyle("#A6E3B8", "#DDF6E5", "note", ""),
    VoiceStyle("#C3A6F2", "#E6D9FB", "note", ""),
    VoiceStyle("#F2C6A6", "#FBE7D9", "note", ""),
)


def voice_style(voice_id: str) -> VoiceStyle:
    if voice_id in VOICE_STYLES:
        return VOICE_STYLES[voice_id]
    return FALLBACK_STYLES[sum(voice_id.encode("utf-8")) % len(FALLBACK_STYLES)]


STYLESHEET = f"""
QWidget {{
    color: {CREAM};
    font-family: {FONT_FAMILY};
    font-size: 10pt;
}}
QWidget#root {{ background: {BACKGROUND}; }}
QFrame#card {{ background: {CARD}; border-radius: 18px; }}
QFrame#divider {{ background: {LINE}; max-height: 1px; min-height: 1px; }}
QLabel {{ background: transparent; }}
QLabel#appTitle {{ font-size: 13.5pt; font-weight: 800; }}
QLabel#version {{ color: {MUTED}; font-size: 9pt; font-weight: 600; }}
QLabel#lamp {{
    font-family: "Segoe UI", sans-serif; font-size: 8.5pt; font-weight: 800;
    padding: 4px 11px; border-radius: 10px; color: #FFFFFF; background: {DANGER};
}}
QLabel#lamp[state="rec"] {{ color: {INK}; background: {SUNFLOWER}; }}
QLabel#pill {{
    padding: 4px 11px; border-radius: 11px; font-size: 9pt; font-weight: 600;
    background: {CARD}; color: {MUTED};
}}
QLabel#pill[state="ok"] {{ color: {OK}; }}
QLabel#pill[state="busy"] {{ color: {SUNFLOWER}; }}
QLabel#pill[state="bad"] {{ color: {DANGER}; }}
QLabel#sectionLabel {{ color: {MUTED}; font-size: 9pt; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; font-size: 9pt; }}
QLabel#value {{ color: {CREAM}; font-size: 10pt; font-weight: 700; }}
QLabel#clock {{ font-size: 14pt; font-weight: 700; font-family: "Consolas", "Segoe UI", monospace; }}
QLabel#heroName {{ font-size: 17pt; font-weight: 800; }}
QLabel#heroCaption {{ font-family: "Segoe UI", sans-serif; font-size: 8.5pt; font-weight: 800; }}
QLabel#liveTitle {{ font-size: 15pt; font-weight: 800; }}
QLabel#notice {{
    background: #3A1F33; border-radius: 12px; padding: 9px 14px; font-size: 9.5pt;
}}
QLabel#resultTag {{
    color: {MUTED}; background: {FIELD}; border-radius: 10px; padding: 8px 12px; font-size: 9.5pt;
}}
QLabel#resultTag[state="fresh"] {{ color: {OK}; }}
QLabel#resultTag[state="stale"] {{ color: {SUNFLOWER}; }}
QLabel#statusBar {{ color: {MUTED}; font-size: 9pt; padding: 0 6px; }}
QLabel#statusBar[state="error"] {{ color: {DANGER}; }}
QLabel#statusBar[state="ok"] {{ color: {OK}; }}

QPushButton {{
    background: {RAISED}; border: 1px solid transparent; border-radius: 10px;
    padding: 7px 14px; color: {CREAM};
}}
QPushButton:hover {{ border-color: {SAKURA}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:focus {{ border-color: {SKY}; }}
QPushButton:disabled {{ color: {DIM}; background: #19224A; }}
QPushButton#primary {{
    background: {SUNFLOWER}; color: {INK}; font-weight: 800; font-size: 11pt; padding: 10px 18px;
}}
QPushButton#primary:hover {{ background: #FFD660; border-color: transparent; }}
QPushButton#primary:pressed {{ background: {SUNFLOWER_DEEP}; }}
QPushButton#primary:disabled {{ background: #3F3C36; color: #8F8870; }}
QPushButton#ghost {{ background: transparent; color: {MUTED}; padding: 5px 10px; font-size: 9pt; }}
QPushButton#ghost:hover {{ color: {SAKURA}; border-color: transparent; }}
QPushButton#ghost:disabled {{ color: {DIM}; }}
QPushButton#tab {{
    background: transparent; color: {MUTED}; font-size: 11pt; font-weight: 700;
    padding: 8px 18px; border-radius: 12px;
}}
QPushButton#tab:hover {{ color: {CREAM}; border-color: transparent; }}
QPushButton#tab:checked {{ background: {RAISED}; color: {CREAM}; }}
QPushButton#segLeft, QPushButton#segRight, QPushButton#segMiddle {{
    padding: 7px 16px; font-weight: 700; background: {FIELD}; color: {MUTED};
}}
QPushButton#segLeft {{ border-top-right-radius: 0; border-bottom-right-radius: 0; }}
QPushButton#segRight {{ border-top-left-radius: 0; border-bottom-left-radius: 0; }}
QPushButton#segLeft:checked, QPushButton#segRight:checked {{ background: {SAKURA}; color: {BACKGROUND}; }}
QPushButton#segLeft:disabled, QPushButton#segRight:disabled {{ color: {DIM}; background: {FIELD}; }}

QComboBox {{
    background: {FIELD}; border: 1px solid transparent; border-radius: 9px;
    padding: 6px 30px 6px 10px; min-height: 20px;
}}
QComboBox:hover, QComboBox:focus {{ border-color: {LINE}; }}
QComboBox:disabled {{ color: {DIM}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {RAISED}; color: {CREAM}; border: 1px solid {LINE};
    selection-background-color: {SAKURA_DEEP}; selection-color: #FFFFFF; outline: none; padding: 4px;
}}

QSlider::groove:horizontal {{ height: 6px; background: {FIELD}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {SKY}, stop:1 {SAKURA}); border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; background: {CREAM};
}}
QSlider::handle:horizontal:hover {{ background: #FFFFFF; }}
QSlider::handle:horizontal:disabled {{ background: {DIM}; }}
QSlider::sub-page:horizontal:disabled {{ background: {LINE}; }}

QProgressBar {{ background: {FIELD}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
QProgressBar::chunk {{ background: {SUNFLOWER}; border-radius: 2px; }}

QToolTip {{ background: {RAISED}; color: {CREAM}; border: 1px solid {LINE}; padding: 5px 8px; }}
"""
