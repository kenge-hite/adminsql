"""Qt stylesheets: polished dark and light themes."""

from __future__ import annotations

ACCENT = "#7d4dff"

_DARK = {
    "bg": "#14121c",
    "sidebar": "#1b1825",
    "card": "#221f2e",
    "card2": "#2a2738",
    "border": "#322f40",
    "text": "#f3f1f8",
    "muted": "#9b97ad",
    "accent": "#7d4dff",
    "accent_hover": "#8d63ff",
    "green": "#1ea885",
    "green_hover": "#27b893",
    "red": "#e5484d",
    "red_hover": "#f05a5f",
    "sel": "rgba(125, 77, 255, 0.18)",
}

_LIGHT = {
    "bg": "#f4f5fa",
    "sidebar": "#ffffff",
    "card": "#ffffff",
    "card2": "#eef0f6",
    "border": "#e3e5ef",
    "text": "#1b1a24",
    "muted": "#6b6878",
    "accent": "#6d3df0",
    "accent_hover": "#7d4dff",
    "green": "#0f9d76",
    "green_hover": "#13b083",
    "red": "#d93a3f",
    "red_hover": "#e5484d",
    "sel": "rgba(125, 77, 255, 0.12)",
}


def palette(theme: str) -> dict:
    return _LIGHT if theme == "light" else _DARK


def build_stylesheet(theme: str = "dark") -> str:
    c = palette(theme)
    return f"""
* {{
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {c['text']};
}}

QMainWindow, #root {{ background: {c['bg']}; }}
QToolTip {{
    background: {c['card2']}; color: {c['text']};
    border: 1px solid {c['border']}; padding: 4px 8px; border-radius: 6px;
}}

/* ---------- Sidebar ---------- */
#sidebar {{
    background: {c['sidebar']};
    border-right: 1px solid {c['border']};
}}
#brand {{ font-size: 15px; font-weight: 800; letter-spacing: 1px; }}
#brandDot {{ color: {c['accent']}; font-size: 15px; font-weight: 800; }}

#searchBox {{
    background: {c['card2']};
    border: 1px solid {c['border']};
    border-radius: 9px;
    padding: 8px 12px;
    color: {c['text']};
}}
#searchBox:focus {{ border: 1px solid {c['accent']}; }}

#serverList {{
    background: transparent; border: none; outline: none;
}}
#serverList::item {{
    border-radius: 10px;
    margin: 2px 0px;
    padding: 0px;
    color: {c['text']};
}}
#serverList::item:hover {{ background: {c['card2']}; }}
#serverList::item:selected {{ background: {c['sel']}; }}

#rowName {{ font-size: 13px; font-weight: 600; }}
#rowHost {{ color: {c['muted']}; font-size: 11px; }}
#rowDot {{ font-size: 12px; color: {c['muted']}; }}
#rowDot[state="on"] {{ color: {c['green']}; }}
#rowDot[state="off"] {{ color: {c['muted']}; }}

#quickConnect, #importBtn {{
    border-radius: 10px; padding: 11px 14px; font-weight: 700;
    border: none;
}}
#quickConnect {{ background: {c['accent']}; color: #ffffff; }}
#quickConnect:hover {{ background: {c['accent_hover']}; }}
#quickConnect:disabled {{ background: {c['card2']}; color: {c['muted']}; }}
#importBtn {{
    background: transparent; color: {c['muted']};
    border: 1px solid {c['border']}; font-weight: 600;
}}
#importBtn:hover {{ background: {c['card2']}; color: {c['text']}; }}

#emptyHint {{ color: {c['muted']}; font-size: 12px; }}

/* ---------- Content ---------- */
#content {{ background: {c['bg']}; }}
#pageTitle {{ font-size: 20px; font-weight: 800; }}
#settingsBtn {{
    background: transparent; border: 1px solid {c['border']};
    border-radius: 9px; padding: 6px 10px; color: {c['muted']}; font-size: 15px;
}}
#settingsBtn:hover {{ background: {c['card2']}; color: {c['text']}; }}

#statusCard, #detailCard, #statCard {{
    background: {c['card']};
    border: 1px solid {c['border']};
    border-radius: 16px;
}}

#statusDot {{ font-size: 13px; }}
#statusDot[state="on"] {{ color: {c['green']}; }}
#statusDot[state="off"] {{ color: {c['muted']}; }}
#statusTitle {{ font-size: 26px; font-weight: 800; }}
#statusTitle[state="on"] {{ color: {c['green']}; }}
#statusServer {{ color: {c['muted']}; font-size: 13px; }}

#connectBtn {{
    border-radius: 12px; padding: 13px 30px;
    font-size: 14px; font-weight: 800; border: none; color: #ffffff;
    background: {c['accent']};
}}
#connectBtn:hover {{ background: {c['accent_hover']}; }}
#connectBtn[state="on"] {{ background: {c['red']}; }}
#connectBtn[state="on"]:hover {{ background: {c['red_hover']}; }}
#connectBtn:disabled {{ background: {c['card2']}; color: {c['muted']}; }}

#statValue {{ font-size: 19px; font-weight: 800; }}
#statValue[accent="down"] {{ color: {c['green']}; }}
#statValue[accent="up"] {{ color: {c['accent']}; }}
#statLabel {{ color: {c['muted']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}

#sectionTitle {{ font-size: 12px; font-weight: 800; letter-spacing: 1px; color: {c['muted']}; }}
#detailKey {{ color: {c['muted']}; font-size: 12px; }}
#detailValue {{ font-size: 13px; font-weight: 600; }}

#ghostBtn, #dangerBtn {{
    border-radius: 9px; padding: 8px 16px; font-weight: 700;
    background: transparent; border: 1px solid {c['border']};
}}
#ghostBtn {{ color: {c['text']}; }}
#ghostBtn:hover {{ background: {c['card2']}; }}
#dangerBtn {{ color: {c['red']}; border: 1px solid {c['red']}; }}
#dangerBtn:hover {{ background: rgba(229, 72, 77, 0.12); }}

#placeholder {{ color: {c['muted']}; font-size: 14px; }}

/* ---------- Dialogs ---------- */
QDialog {{ background: {c['bg']}; }}
#dialogTitle {{ font-size: 16px; font-weight: 800; }}
#configText {{
    background: {c['card']}; border: 1px solid {c['border']}; border-radius: 10px;
    font-family: "Cascadia Code", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px; padding: 8px;
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid {c['border']}; background: {c['card2']};
}}
QCheckBox::indicator:checked {{ background: {c['accent']}; border: 1px solid {c['accent']}; }}
QComboBox {{
    background: {c['card2']}; border: 1px solid {c['border']};
    border-radius: 8px; padding: 6px 10px; min-width: 120px;
}}
QComboBox QAbstractItemView {{
    background: {c['card']}; border: 1px solid {c['border']};
    selection-background-color: {c['sel']}; outline: none;
}}
#primaryBtn {{
    background: {c['accent']}; color: #fff; border: none;
    border-radius: 9px; padding: 8px 18px; font-weight: 700;
}}
#primaryBtn:hover {{ background: {c['accent_hover']}; }}

/* ---------- Misc ---------- */
QMenu {{
    background: {c['card']}; border: 1px solid {c['border']};
    border-radius: 10px; padding: 6px;
}}
QMenu::item {{ padding: 8px 22px 8px 14px; border-radius: 7px; }}
QMenu::item:selected {{ background: {c['card2']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 6px 4px; }}

#statusBar {{ color: {c['muted']}; font-size: 11px; }}

QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""
