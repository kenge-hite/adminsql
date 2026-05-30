"""Qt stylesheet for a clean, minimal look."""

# A restrained light theme: one accent colour, generous spacing, rounded edges.
ACCENT = "#2f6df6"
ACCENT_HOVER = "#2a61dd"
DANGER = "#e5484d"
DANGER_HOVER = "#cf3a3f"

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    color: #1d2433;
}}

QMainWindow, #root {{
    background: #f5f6f8;
}}

/* ---- Sidebar ---- */
#sidebar {{
    background: #ffffff;
    border-right: 1px solid #e6e8ec;
}}

#sidebarTitle {{
    font-size: 13px;
    font-weight: 600;
    color: #8a93a3;
    padding: 4px 6px;
}}

QListWidget {{
    border: none;
    background: transparent;
    outline: 0;
}}

QListWidget::item {{
    padding: 11px 12px;
    border-radius: 8px;
    margin: 2px 0;
    color: #364152;
}}

QListWidget::item:hover {{
    background: #f0f3fa;
}}

QListWidget::item:selected {{
    background: #e7eefe;
    color: {ACCENT};
    font-weight: 600;
}}

/* ---- Buttons ---- */
QPushButton {{
    border: 1px solid #d7dbe2;
    border-radius: 8px;
    padding: 7px 14px;
    background: #ffffff;
    color: #364152;
}}

QPushButton:hover {{
    background: #f0f3fa;
}}

QPushButton:disabled {{
    color: #aab1bd;
    background: #f3f4f6;
}}

QPushButton#iconButton {{
    padding: 4px 10px;
    font-size: 18px;
    font-weight: 600;
    min-width: 18px;
}}

QPushButton#primary {{
    background: {ACCENT};
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 12px 18px;
    font-size: 15px;
}}

QPushButton#primary:hover {{
    background: {ACCENT_HOVER};
}}

QPushButton#danger {{
    background: {DANGER};
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 12px 18px;
    font-size: 15px;
}}

QPushButton#danger:hover {{
    background: {DANGER_HOVER};
}}

/* ---- Detail panel ---- */
#detailCard {{
    background: #ffffff;
    border: 1px solid #e6e8ec;
    border-radius: 14px;
}}

#tunnelName {{
    font-size: 22px;
    font-weight: 700;
}}

#fieldLabel {{
    color: #8a93a3;
    font-size: 12px;
    font-weight: 600;
}}

#fieldValue {{
    color: #1d2433;
    font-size: 14px;
}}

#statusBadge {{
    border-radius: 11px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 700;
}}

#statusBadge[state="on"] {{
    background: #e4f7ec;
    color: #1f9254;
}}

#statusBadge[state="off"] {{
    background: #f0f1f3;
    color: #8a93a3;
}}

#emptyHint {{
    color: #8a93a3;
    font-size: 15px;
}}

#statusBar {{
    color: #8a93a3;
    font-size: 12px;
}}
"""
