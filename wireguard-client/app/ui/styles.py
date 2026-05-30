"""Qt stylesheet: compact, minimal dark theme (Proton VPN inspired)."""

ACCENT = "#7d4dff"        # purple, idle/primary
ACCENT_HOVER = "#8d63ff"
CONNECTED = "#1ea885"     # green, connected
CONNECTED_HOVER = "#27b893"
BG = "#16141f"
CARD = "#221f2e"
CARD_HOVER = "#2b2839"
TEXT = "#ffffff"
MUTED = "#9b97ad"

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {TEXT};
}}

QMainWindow, #root {{
    background: {BG};
}}

#brand {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 1px;
}}

#brandDot {{
    color: {ACCENT};
    font-size: 15px;
    font-weight: 700;
}}

/* ---- Central power button ---- */
#powerButton {{
    border-radius: 74px;
    min-width: 148px;
    max-width: 148px;
    min-height: 148px;
    max-height: 148px;
    font-size: 52px;
    color: {TEXT};
    border: 3px solid {ACCENT};
    background: rgba(125, 77, 255, 0.12);
}}

#powerButton:hover {{
    background: rgba(125, 77, 255, 0.22);
}}

#powerButton[state="on"] {{
    border: 3px solid {CONNECTED};
    background: rgba(30, 168, 133, 0.18);
    color: {CONNECTED};
}}

#powerButton[state="on"]:hover {{
    background: rgba(30, 168, 133, 0.28);
}}

#powerButton:disabled {{
    border: 3px solid #3a3747;
    background: transparent;
    color: #56536a;
}}

/* ---- Status text ---- */
#statusTitle {{
    font-size: 21px;
    font-weight: 700;
}}

#statusTitle[state="on"] {{
    color: {CONNECTED};
}}

#statusTitle[state="off"] {{
    color: {TEXT};
}}

#statusSub {{
    color: {MUTED};
    font-size: 13px;
}}

/* ---- Server selector card ---- */
#serverCard {{
    background: {CARD};
    border: 1px solid #322f40;
    border-radius: 12px;
    padding: 12px 14px;
    text-align: left;
}}

#serverCard:hover {{
    background: {CARD_HOVER};
}}

#serverCard:disabled {{
    color: {MUTED};
}}

#cardLabel {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
}}

#cardName {{
    color: {TEXT};
    font-size: 15px;
    font-weight: 600;
}}

#cardEndpoint {{
    color: {MUTED};
    font-size: 12px;
}}

#chevron {{
    color: {MUTED};
    font-size: 16px;
}}

/* ---- Popup menu (server list) ---- */
QMenu {{
    background: {CARD};
    border: 1px solid #322f40;
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 22px 8px 14px;
    border-radius: 7px;
    color: {TEXT};
}}

QMenu::item:selected {{
    background: {CARD_HOVER};
}}

QMenu::separator {{
    height: 1px;
    background: #322f40;
    margin: 6px 4px;
}}

#statusBar {{
    color: {MUTED};
    font-size: 11px;
}}

QMessageBox {{
    background: {BG};
}}
"""
