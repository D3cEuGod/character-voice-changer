"""广播室调音台的配色与样式表。颜色取自 assets/taffy-avatar.jpg：樱粉头发、海军蓝贝雷帽、向日葵黄。"""
from dataclasses import dataclass

NAVY_900 = "#111930"
NAVY_800 = "#18223F"
NAVY_700 = "#222F58"
NAVY_600 = "#34447A"
NAVY_500 = "#4A5C9A"
SAKURA = "#F7B9CB"
SAKURA_DEEP = "#EC86A6"
SUNFLOWER = "#F8C537"
SUNFLOWER_DEEP = "#E3A012"
SKY = "#7CC4F2"
CREAM = "#FFF7EC"
MUTED = "#A9B4D6"
DIM = "#6D779B"
DANGER = "#FF5C7A"
OK = "#7BE0A6"
INK = "#2A1E00"

FONT_FAMILY = '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif'


@dataclass(frozen=True)
class VoiceStyle:
    color: str      # 角色色
    accent: str     # 高亮色
    art: str        # avatar | mic | guitar | note


# 角色名字来自 GET /api/voices；这里只为已知 id 配美术。未知 id 用通用音符图案。
VOICE_STYLES = {
    "taffy": VoiceStyle(SAKURA, SUNFLOWER, "avatar"),
    "tomori": VoiceStyle("#77BBDD", "#C8E8F7", "mic"),
    "anon": VoiceStyle("#FF8899", "#FFD0D8", "guitar"),
}
FALLBACK_STYLES = (
    VoiceStyle("#A6E3B8", "#DDF6E5", "note"),
    VoiceStyle("#C3A6F2", "#E6D9FB", "note"),
    VoiceStyle("#F2C6A6", "#FBE7D9", "note"),
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
QWidget#root {{ background: {NAVY_900}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QFrame#header {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {NAVY_700}, stop:1 {NAVY_800});
    border: 1px solid {NAVY_600};
    border-radius: 14px;
}}
QLabel#appTitle {{ font-size: 15pt; font-weight: 700; color: {CREAM}; }}
QLabel#appSubtitle {{ font-size: 9pt; color: {MUTED}; }}
QLabel#lamp {{
    font-family: "Segoe UI", sans-serif; font-size: 9pt; font-weight: 800;
    padding: 5px 12px; border-radius: 10px;
    color: {DIM}; background: {NAVY_900}; border: 1px solid {NAVY_600};
}}
QLabel#lamp[state="live"] {{ color: #FFFFFF; background: {DANGER}; border: 1px solid #FFB3C1; }}
QLabel#lamp[state="rec"] {{ color: {INK}; background: {SUNFLOWER}; border: 1px solid #FFE08A; }}
QLabel#pill {{
    padding: 5px 12px; border-radius: 12px; font-size: 9pt; font-weight: 600;
    background: {NAVY_900}; border: 1px solid {NAVY_600}; color: {MUTED};
}}
QLabel#pill[state="ok"] {{ color: {OK}; border: 1px solid #3C8F68; }}
QLabel#pill[state="busy"] {{ color: {SUNFLOWER}; border: 1px solid {SUNFLOWER_DEEP}; }}
QLabel#pill[state="bad"] {{ color: {DANGER}; border: 1px solid {DANGER}; }}

QFrame#panel {{
    background: {NAVY_800};
    border: 1px solid {NAVY_600};
    border-radius: 14px;
}}
QLabel#panelTitle {{ color: {SUNFLOWER}; font-size: 10.5pt; font-weight: 700; }}
QLabel#panelHint {{ color: {MUTED}; font-size: 9pt; }}
QLabel#muted {{ color: {MUTED}; font-size: 9pt; }}
QLabel#fieldLabel {{ color: {SAKURA}; font-size: 9pt; font-weight: 600; }}
QLabel#bigValue {{ color: {SUNFLOWER}; font-size: 20pt; font-weight: 700; }}
QLabel#clock {{ color: {CREAM}; font-size: 15pt; font-weight: 700; font-family: "Consolas", "Segoe UI", monospace; }}
QLabel#heroName {{ color: {CREAM}; font-size: 19pt; font-weight: 800; }}
QLabel#heroCaption {{ color: {MUTED}; font-size: 9pt; font-weight: 600; }}
QLabel#notice {{
    color: {CREAM}; background: #3A1F33; border: 1px solid {DANGER}; border-radius: 10px;
    padding: 8px 12px; font-size: 9.5pt;
}}
QLabel#headphones {{
    color: {INK}; background: {SUNFLOWER}; border-radius: 9px; padding: 5px 10px;
    font-size: 9pt; font-weight: 700;
}}
QLabel#resultTag {{
    color: {CREAM}; background: {NAVY_900}; border: 1px dashed {NAVY_500}; border-radius: 9px;
    padding: 7px 10px; font-size: 9.5pt;
}}
QLabel#resultTag[state="fresh"] {{ border: 1px solid {OK}; color: {OK}; }}
QLabel#resultTag[state="stale"] {{ border: 1px dashed {SUNFLOWER_DEEP}; color: {SUNFLOWER}; }}
QLabel#statusBar {{ color: {MUTED}; font-size: 9.5pt; padding: 2px 6px; }}
QLabel#statusBar[state="error"] {{ color: {DANGER}; }}
QLabel#statusBar[state="ok"] {{ color: {OK}; }}

QPushButton {{
    background: {NAVY_700}; border: 1px solid {NAVY_600}; border-radius: 10px;
    padding: 7px 14px; color: {CREAM};
}}
QPushButton:hover {{ border-color: {SAKURA}; }}
QPushButton:pressed {{ background: {NAVY_600}; }}
QPushButton:focus {{ border-color: {SKY}; }}
QPushButton:disabled {{ color: {DIM}; background: #1B2545; border-color: #29355F; }}
QPushButton#primary {{
    background: {SUNFLOWER}; color: {INK}; border: 1px solid #FFE08A; font-weight: 800;
    font-size: 11pt; padding: 10px 18px;
}}
QPushButton#primary:hover {{ background: #FFD660; }}
QPushButton#primary:pressed {{ background: {SUNFLOWER_DEEP}; }}
QPushButton#primary:disabled {{ background: #4B4733; color: #9D9578; border-color: #5A553E; }}
QPushButton#ghost {{ background: transparent; border: 1px solid {NAVY_600}; padding: 5px 10px; font-size: 9pt; }}
QPushButton#ghost:hover {{ border-color: {SAKURA}; color: {SAKURA}; }}
QPushButton#ghost:disabled {{ color: {DIM}; border-color: #29355F; }}
QPushButton#segLeft, QPushButton#segRight {{
    padding: 8px 18px; font-weight: 700; background: {NAVY_900}; border: 1px solid {NAVY_600};
}}
QPushButton#segLeft {{ border-top-right-radius: 0; border-bottom-right-radius: 0; }}
QPushButton#segRight {{ border-top-left-radius: 0; border-bottom-left-radius: 0; border-left: none; }}
QPushButton#segLeft:checked {{ background: {SKY}; color: {NAVY_900}; border-color: {SKY}; }}
QPushButton#segRight:checked {{ background: {SAKURA}; color: {NAVY_900}; border-color: {SAKURA}; }}
QPushButton#segLeft:disabled, QPushButton#segRight:disabled {{ color: {DIM}; background: #161F3A; }}

QComboBox {{
    background: {NAVY_900}; border: 1px solid {NAVY_600}; border-radius: 8px;
    padding: 6px 30px 6px 10px; min-height: 20px;
}}
QComboBox:hover, QComboBox:focus {{ border-color: {SAKURA}; }}
QComboBox:disabled {{ color: {DIM}; border-color: #29355F; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {NAVY_700}; color: {CREAM}; border: 1px solid {NAVY_500};
    selection-background-color: {SAKURA_DEEP}; selection-color: #FFFFFF; outline: none;
    padding: 4px;
}}

QSlider::groove:horizontal {{
    height: 8px; background: #0B1122; border: 1px solid {NAVY_600}; border-radius: 5px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {SKY}, stop:1 {SAKURA});
    border-radius: 5px;
}}
QSlider::handle:horizontal {{
    width: 16px; height: 26px; margin: -10px 0; border-radius: 6px;
    background: {CREAM}; border: 2px solid {SUNFLOWER};
}}
QSlider::handle:horizontal:hover {{ background: #FFFFFF; border-color: {SAKURA_DEEP}; }}
QSlider::handle:horizontal:disabled {{ background: {DIM}; border-color: {NAVY_600}; }}
QSlider::sub-page:horizontal:disabled {{ background: {NAVY_600}; }}

QProgressBar {{
    background: #0B1122; border: 1px solid {NAVY_600}; border-radius: 4px; max-height: 6px; min-height: 6px;
}}
QProgressBar::chunk {{ background: {SUNFLOWER}; border-radius: 3px; }}

QToolTip {{
    background: {NAVY_700}; color: {CREAM}; border: 1px solid {SAKURA}; padding: 5px 8px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {NAVY_600}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""
