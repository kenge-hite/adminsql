"""Main application window: animated two-pane WireGuard client."""

from __future__ import annotations

import random
import time

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..settings import Settings
from ..wireguard import (
    TunnelInfo,
    WireGuardError,
    WireGuardManager,
    human_bytes,
    human_duration,
    human_rate,
)
from .icon import make_app_icon
from .styles import build_stylesheet, palette
from .widgets import PowerButton, PulseDot, Sparkline

DOT = "\u25cf"
PIN = "\u2605"
COPY = "\u29c9"

ACCENTS = [
    ("Violet", "#7d4dff"),
    ("Ocean", "#2f8bff"),
    ("Emerald", "#1ea885"),
    ("Sunset", "#ff6b4d"),
    ("Magenta", "#e052b0"),
]


def _shorten(text: str, head: int = 10, tail: int = 6) -> str:
    if len(text) <= head + tail + 1:
        return text
    return f"{text[:head]}\u2026{text[-tail:]}"


class ServerRow(QWidget):
    """Custom row widget shown inside the sidebar server list."""

    def __init__(self, tunnel: TunnelInfo, pinned: bool = False) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)
        self.dot = QLabel(DOT, objectName="rowDot")
        self.dot.setProperty("state", "off")
        row.addWidget(self.dot, alignment=Qt.AlignVCenter)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        texts.addWidget(QLabel(tunnel.name, objectName="rowName"))
        texts.addWidget(QLabel(tunnel.host or tunnel.address or "", objectName="rowHost"))
        row.addLayout(texts, stretch=1)
        self.pin = QLabel(PIN if pinned else "", objectName="rowPin")
        row.addWidget(self.pin, alignment=Qt.AlignVCenter)

    def set_connected(self, connected: bool) -> None:
        self.dot.setProperty("state", "on" if connected else "off")
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)


class MainWindow(QMainWindow):
    def __init__(self, manager: WireGuardManager | None = None) -> None:
        super().__init__()
        self.manager = manager or WireGuardManager()
        self.settings = Settings.load()
        self._connected: dict[str, bool] = {}
        self._since: dict[str, float] = {}
        self._tunnels: list[TunnelInfo] = []
        self._current: str | None = None
        self._connecting = False
        # rate tracking: name -> (timestamp, rx, tx)
        self._samples: dict[str, tuple[float, int, int]] = {}
        self._demo_bytes: dict[str, tuple[int, int]] = {}

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 600)
        self.setWindowIcon(make_app_icon())
        self._restore_geometry()
        self._apply_theme()

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_content(), stretch=1)

        self.statusBar().setObjectName("statusBar")
        self.statusBar().showMessage(f"{APP_NAME} v{__version__}")

        self._build_tray()
        self._sync_power_colors()
        self.refresh_tunnels(select=self.settings.last_tunnel or None)

        self._poll = QTimer(self)
        self._poll.setInterval(2000)
        self._poll.timeout.connect(self._poll_status)
        self._poll.start()

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._update_stats)
        self._tick.start()

        if self.settings.connect_on_launch and self._current:
            QTimer.singleShot(300, lambda: self._do_connect(quiet=True))

    # ------------------------------------------------------------------ sidebar
    def _build_sidebar(self) -> QWidget:
        bar = QFrame(objectName="sidebar")
        bar.setFixedWidth(258)
        col = QVBoxLayout(bar)
        col.setContentsMargins(16, 18, 16, 16)
        col.setSpacing(12)

        brand = QHBoxLayout()
        brand.addWidget(QLabel(DOT, objectName="brandDot"))
        brand.addSpacing(6)
        brand.addWidget(QLabel("WIREGUARD", objectName="brand"))
        brand.addStretch(1)
        col.addLayout(brand)

        self.quick = QPushButton("Quick Connect", objectName="quickConnect")
        self.quick.setCursor(Qt.PointingHandCursor)
        self.quick.clicked.connect(self._quick_connect)
        col.addWidget(self.quick)

        self.search = QLineEdit(objectName="searchBox")
        self.search.setPlaceholderText("Search servers\u2026")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_list)
        col.addWidget(self.search)

        self.recent_label = QLabel("RECENT", objectName="recentLabel")
        col.addWidget(self.recent_label)
        self.recent_row = QHBoxLayout()
        self.recent_row.setSpacing(6)
        self.recent_row.setContentsMargins(0, 0, 0, 0)
        recent_wrap = QWidget()
        recent_wrap.setLayout(self.recent_row)
        col.addWidget(recent_wrap)

        self.list = QListWidget(objectName="serverList")
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._row_menu)
        self.list.currentItemChanged.connect(self._on_select)
        col.addWidget(self.list, stretch=1)

        self.empty_hint = QLabel("No servers yet.\nImport a .conf below.", objectName="emptyHint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setWordWrap(True)
        col.addWidget(self.empty_hint)

        imp = QPushButton("+  Import config", objectName="importBtn")
        imp.setCursor(Qt.PointingHandCursor)
        imp.clicked.connect(self.import_config)
        col.addWidget(imp)
        return bar

    # ------------------------------------------------------------------ content
    def _build_content(self) -> QWidget:
        page = QFrame(objectName="content")
        col = QVBoxLayout(page)
        col.setContentsMargins(26, 22, 26, 18)
        col.setSpacing(18)

        header = QHBoxLayout()
        header.addWidget(QLabel("Connection", objectName="pageTitle"))
        header.addStretch(1)
        about = QPushButton("\u2139", objectName="settingsBtn")
        about.setCursor(Qt.PointingHandCursor)
        about.setToolTip("About")
        about.clicked.connect(self.open_about)
        header.addWidget(about)
        gear = QPushButton("\u2699", objectName="settingsBtn")
        gear.setCursor(Qt.PointingHandCursor)
        gear.setToolTip("Settings")
        gear.clicked.connect(self.open_settings)
        header.addWidget(gear)
        col.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_dashboard())
        self.stack.addWidget(self._build_placeholder())
        col.addWidget(self.stack, stretch=1)
        return page

    def _build_placeholder(self) -> QWidget:
        w = QWidget()
        box = QVBoxLayout(w)
        box.addStretch(1)
        lbl = QLabel("No server selected.\nImport a WireGuard config to get started.",
                     objectName="placeholder")
        lbl.setAlignment(Qt.AlignCenter)
        box.addWidget(lbl)
        btn = QPushButton("+  Import config", objectName="quickConnect")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(200)
        btn.clicked.connect(self.import_config)
        box.addSpacing(12)
        box.addWidget(btn, alignment=Qt.AlignHCenter)
        box.addStretch(2)
        return w

    def _build_dashboard(self) -> QWidget:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(16)

        # hero card with big power button
        hero = QFrame(objectName="heroCard")
        hbox = QVBoxLayout(hero)
        hbox.setContentsMargins(22, 22, 22, 22)
        hbox.setSpacing(10)

        self.power = PowerButton(diameter=164)
        self.power.clicked.connect(self.toggle_connection)
        hbox.addWidget(self.power, alignment=Qt.AlignHCenter)

        statusrow = QHBoxLayout()
        statusrow.setSpacing(8)
        statusrow.addStretch(1)
        self.status_dot = PulseDot(diameter=11)
        statusrow.addWidget(self.status_dot, alignment=Qt.AlignVCenter)
        self.status_title = QLabel("Disconnected", objectName="heroStatus")
        self.status_title.setProperty("state", "off")
        statusrow.addWidget(self.status_title)
        statusrow.addStretch(1)
        hbox.addLayout(statusrow)

        self.status_server = QLabel("", objectName="heroServer")
        self.status_server.setAlignment(Qt.AlignHCenter)
        hbox.addWidget(self.status_server)
        self.status_duration = QLabel("", objectName="heroDuration")
        self.status_duration.setAlignment(Qt.AlignHCenter)
        hbox.addWidget(self.status_duration)
        col.addWidget(hero)

        # stat cards
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_down = self._stat_card(stats, "DOWNLOAD", accent="down", spark=True)
        self.stat_up = self._stat_card(stats, "UPLOAD", accent="up", spark=True)
        col.addLayout(stats)

        # details
        det = QFrame(objectName="detailCard")
        dl = QVBoxLayout(det)
        dl.setContentsMargins(22, 18, 22, 18)
        dl.setSpacing(12)
        dl.addWidget(QLabel("TUNNEL DETAILS", objectName="sectionTitle"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        self._detail_values: dict[str, QLabel] = {}
        fields = [
            ("Address", "address"), ("DNS", "dns"),
            ("Endpoint", "endpoint"), ("Allowed IPs", "allowed_ips"),
            ("Public key", "public_key"), ("Latest handshake", "handshake"),
        ]
        for i, (label, key) in enumerate(fields):
            r, c0 = divmod(i, 2)
            grid.addWidget(QLabel(label, objectName="detailKey"), r, c0 * 2)
            val = QLabel("\u2014", objectName="detailValue")
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._detail_values[key] = val
            grid.addWidget(val, r, c0 * 2 + 1)
        dl.addLayout(grid)

        actions = QHBoxLayout()
        ckey = QPushButton(f"{COPY}  Copy key", objectName="ghostBtn")
        ckey.setCursor(Qt.PointingHandCursor)
        ckey.clicked.connect(lambda: self._copy_field("public_key"))
        cep = QPushButton(f"{COPY}  Copy endpoint", objectName="ghostBtn")
        cep.setCursor(Qt.PointingHandCursor)
        cep.clicked.connect(lambda: self._copy_field("endpoint"))
        actions.addWidget(ckey)
        actions.addWidget(cep)
        actions.addStretch(1)
        view = QPushButton("View config", objectName="ghostBtn")
        view.setCursor(Qt.PointingHandCursor)
        view.clicked.connect(self.view_config)
        remove = QPushButton("Remove", objectName="dangerBtn")
        remove.setCursor(Qt.PointingHandCursor)
        remove.clicked.connect(self.delete_tunnel)
        actions.addWidget(view)
        actions.addWidget(remove)
        dl.addLayout(actions)
        col.addWidget(det)
        col.addStretch(1)
        return w

    def _stat_card(self, parent: QHBoxLayout, label: str,
                   accent: str = "", spark: bool = False) -> dict:
        card = QFrame(objectName="statCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 14, 18, 14)
        box.setSpacing(2)
        top = QHBoxLayout()
        value = QLabel("\u2014", objectName="statValue")
        if accent:
            value.setProperty("accent", accent)
        top.addWidget(value)
        top.addStretch(1)
        rate = QLabel("", objectName="statRate")
        top.addWidget(rate, alignment=Qt.AlignBottom)
        box.addLayout(top)
        box.addWidget(QLabel(label, objectName="statLabel"))
        line = None
        if spark:
            line = Sparkline(capacity=44)
            box.addWidget(line)
        parent.addWidget(card, stretch=1)
        return {"value": value, "rate": rate, "spark": line}

    # ------------------------------------------------------------------ tray
    def _build_tray(self) -> None:
        self.tray: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        self.tray_toggle = QAction("Connect", self)
        self.tray_toggle.triggered.connect(self.toggle_connection)
        show = QAction("Show window", self)
        show.triggered.connect(self._show_normal)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(self.tray_toggle)
        menu.addSeparator()
        menu.addAction(show)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._show_normal()

    def _notify(self, title: str, message: str, connected: bool = False) -> None:
        if self.tray and self.settings.notifications:
            self.tray.showMessage(title, message, make_app_icon(connected), 3000)

    def _show_normal(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._force_quit = True
        QApplication.quit()

    # ------------------------------------------------------------------ data
    def _order_tunnels(self, tunnels: list[TunnelInfo]) -> list[TunnelInfo]:
        pinned = self.settings.pinned
        return sorted(
            tunnels,
            key=lambda t: (
                0 if t.name in pinned else 1,
                pinned.index(t.name) if t.name in pinned else 0,
                t.name.lower(),
            ),
        )

    def refresh_tunnels(self, select: str | None = None) -> None:
        self._tunnels = self._order_tunnels(self.manager.list_tunnels())
        names = [t.name for t in self._tunnels]
        if select and select in names:
            self._current = select
        elif self._current not in names:
            self._current = names[0] if names else None

        self.list.blockSignals(True)
        self.list.clear()
        for tunnel in self._tunnels:
            item = QListWidgetItem(self.list)
            item.setData(Qt.UserRole, tunnel.name)
            widget = ServerRow(tunnel, pinned=tunnel.name in self.settings.pinned)
            widget.set_connected(self._connected.get(tunnel.name, False))
            item.setSizeHint(widget.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)
            if tunnel.name == self._current:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)

        self.empty_hint.setVisible(not self._tunnels)
        has = self._current is not None
        self.quick.setEnabled(has)
        self.stack.setCurrentIndex(0 if has else 1)
        self._filter_list(self.search.text())
        self._rebuild_recent()
        self.update_detail()

    def _rebuild_recent(self) -> None:
        while self.recent_row.count():
            item = self.recent_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        names = [t.name for t in self._tunnels]
        recents = [n for n in self.settings.recent if n in names][:4]
        for name in recents:
            chip = QPushButton(name, objectName="recentChip")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _=False, n=name: self._select_name(n))
            self.recent_row.addWidget(chip)
        self.recent_row.addStretch(1)
        visible = bool(recents)
        self.recent_label.setVisible(visible)

    def _select_name(self, name: str) -> None:
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == name:
                self.list.setCurrentRow(i)
                return

    def current_tunnel(self) -> TunnelInfo | None:
        for tunnel in self._tunnels:
            if tunnel.name == self._current:
                return tunnel
        return None

    def _on_select(self, current: QListWidgetItem | None, _prev=None) -> None:
        if current is None:
            return
        self._current = current.data(Qt.UserRole)
        self.settings.last_tunnel = self._current or ""
        self.settings.save()
        self._fade_in(self.stack.currentWidget())
        self.update_detail()

    def _filter_list(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            name = (item.data(Qt.UserRole) or "").lower()
            item.setHidden(bool(needle) and needle not in name)

    def _row_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        name = item.data(Qt.UserRole)
        menu = QMenu(self)
        pinned = name in self.settings.pinned
        act_pin = menu.addAction("Unpin" if pinned else "Pin to top")
        act_view = menu.addAction("View config")
        menu.addSeparator()
        act_del = menu.addAction("Remove")
        chosen = menu.exec(self.list.mapToGlobal(pos))
        if chosen == act_pin:
            self.settings.toggle_pin(name)
            self.settings.save()
            self.refresh_tunnels(select=self._current)
        elif chosen == act_view:
            self._current = name
            self.view_config()
        elif chosen == act_del:
            self._current = name
            self.delete_tunnel()

    def update_detail(self) -> None:
        tunnel = self.current_tunnel()
        if tunnel is None:
            self.stack.setCurrentIndex(1)
            return
        self.stack.setCurrentIndex(0)
        self.status_server.setText(tunnel.endpoint or tunnel.address or tunnel.name)
        self._detail_values["address"].setText(tunnel.address or "\u2014")
        self._detail_values["dns"].setText(tunnel.dns or "\u2014")
        self._detail_values["endpoint"].setText(tunnel.endpoint or "\u2014")
        self._detail_values["allowed_ips"].setText(tunnel.allowed_ips or "\u2014")
        self._detail_values["public_key"].setText(_shorten(tunnel.public_key) or "\u2014")
        self._render_state()
        self._update_stats()

    def _render_state(self) -> None:
        name = self._current
        connected = self._connected.get(name, False) if name else False
        if self._connecting:
            state = "connecting"
        elif connected:
            state = "on"
        else:
            state = "off"

        self.power.set_state(state)
        c = palette(self.settings.theme, self.settings.accent)
        self.status_dot.set_color(c["green"] if connected else c["muted"])
        self.status_dot.set_active(connected)
        self._set_prop(self.status_title, "state", state)
        title = {"on": "Connected", "connecting": "Connecting\u2026",
                 "off": "Disconnected"}[state]
        self.status_title.setText(title)

        self.connect_label = "Disconnect" if connected else "Connect"
        self.quick.setText("Disconnect" if connected else "Quick Connect")
        if getattr(self, "tray_toggle", None):
            self.tray_toggle.setText(self.connect_label)
        if self.tray:
            self.tray.setIcon(make_app_icon(connected))
        self.setWindowIcon(make_app_icon(connected))
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, ServerRow):
                widget.set_connected(self._connected.get(item.data(Qt.UserRole), False))

    def _update_stats(self) -> None:
        name = self._current
        connected = self._connected.get(name, False) if name else False
        if not connected:
            self.stat_down["value"].setText("\u2014")
            self.stat_up["value"].setText("\u2014")
            self.stat_down["rate"].setText("")
            self.stat_up["rate"].setText("")
            self.status_duration.setText("")
            self._detail_values["handshake"].setText("\u2014")
            return
        since = self._since.get(name, time.time())
        self.status_duration.setText("\u23f1  " + human_duration(int(time.time() - since)))

    # ------------------------------------------------------------------ actions
    def _copy_field(self, key: str) -> None:
        tunnel = self.current_tunnel()
        if not tunnel:
            return
        value = {"public_key": tunnel.public_key, "endpoint": tunnel.endpoint}.get(key, "")
        if not value:
            self.statusBar().showMessage("Nothing to copy", 2500)
            return
        QGuiApplication.clipboard().setText(value)
        self.statusBar().showMessage(f"Copied {key.replace('_', ' ')} to clipboard", 2500)

    def import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import WireGuard config", "", "WireGuard config (*.conf)"
        )
        if not path:
            return
        try:
            tunnel = self.manager.import_config(path)
        except WireGuardError as exc:
            self._error(str(exc))
            return
        self.refresh_tunnels(select=tunnel.name)
        self.statusBar().showMessage(f"Imported '{tunnel.name}'", 4000)

    def delete_tunnel(self) -> None:
        name = self._current
        if not name:
            return
        if QMessageBox.question(
            self, "Remove server",
            f"Remove '{name}'? This deletes the imported config copy.",
        ) != QMessageBox.Yes:
            return
        if self._connected.get(name):
            try:
                self.manager.disconnect(name)
            except WireGuardError:
                pass
        self._connected.pop(name, None)
        self._since.pop(name, None)
        self._samples.pop(name, None)
        self._demo_bytes.pop(name, None)
        if name in self.settings.pinned:
            self.settings.pinned.remove(name)
        if name in self.settings.recent:
            self.settings.recent.remove(name)
        self.settings.save()
        self.manager.delete_tunnel(name)
        self._current = None
        self.refresh_tunnels()
        self.statusBar().showMessage(f"Removed '{name}'", 4000)

    def view_config(self) -> None:
        name = self._current
        if not name:
            return
        try:
            text = self.manager.config_text(name, mask_secrets=True)
        except WireGuardError as exc:
            self._error(str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{name} \u2014 config")
        dialog.resize(440, 380)
        box = QVBoxLayout(dialog)
        box.addWidget(QLabel(f"{name}.conf  (private key hidden)", objectName="dialogTitle"))
        editor = QPlainTextEdit(objectName="configText")
        editor.setReadOnly(True)
        editor.setPlainText(text)
        box.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        box.addWidget(buttons)
        dialog.exec()

    def _quick_connect(self) -> None:
        if not self._current:
            return
        self.toggle_connection()

    def toggle_connection(self) -> None:
        name = self._current
        if not name or self._connecting:
            return
        if self._connected.get(name):
            self._do_disconnect()
        else:
            self._begin_connect()

    def _begin_connect(self) -> None:
        name = self._current
        if not name:
            return
        self._connecting = True
        self._render_state()
        self.statusBar().showMessage(f"Connecting to '{name}'\u2026", 2000)
        QTimer.singleShot(900, lambda: self._do_connect(name))

    def _do_connect(self, name: str | None = None, quiet: bool = False) -> None:
        name = name or self._current
        if not name:
            self._connecting = False
            return
        try:
            if self.settings.demo_mode:
                self._demo_bytes[name] = (0, 0)
            else:
                self.manager.connect(name)
            self._connected[name] = True
            self._since[name] = time.time()
            self._samples.pop(name, None)
            self.settings.mark_recent(name)
            self.settings.save()
            self._reset_sparks()
            self.statusBar().showMessage(f"Connected '{name}'", 4000)
            self._notify(APP_NAME, f"Connected to {name}", connected=True)
        except WireGuardError as exc:
            if quiet:
                self.statusBar().showMessage(str(exc), 8000)
            else:
                self._error(str(exc))
        finally:
            self._connecting = False
        self._render_state()
        self._rebuild_recent()
        self._update_stats()

    def _do_disconnect(self) -> None:
        name = self._current
        if not name:
            return
        try:
            if not self.settings.demo_mode:
                self.manager.disconnect(name)
        except WireGuardError as exc:
            self._error(str(exc))
        self._connected[name] = False
        self._since.pop(name, None)
        self._samples.pop(name, None)
        self._demo_bytes.pop(name, None)
        self._reset_sparks()
        self.statusBar().showMessage(f"Disconnected '{name}'", 4000)
        self._notify(APP_NAME, f"Disconnected from {name}")
        self._render_state()
        self._update_stats()

    def _reset_sparks(self) -> None:
        for stat in (self.stat_down, self.stat_up):
            if stat["spark"]:
                stat["spark"].reset()

    def _poll_status(self) -> None:
        name = self._current
        if not name:
            return
        if self.settings.demo_mode and self._connected.get(name):
            self._poll_demo(name)
            return
        try:
            status = self.manager.status(name)
        except WireGuardError:
            return
        self._connected[name] = status.connected
        if status.connected and name not in self._since:
            self._since[name] = time.time()
        if status.connected:
            self._apply_traffic(name, status.rx_bytes, status.tx_bytes)
            self._detail_values["handshake"].setText(status.last_handshake or "\u2014")
        self._render_state()

    def _poll_demo(self, name: str) -> None:
        rx, tx = self._demo_bytes.get(name, (0, 0))
        rx += random.randint(40_000, 900_000)
        tx += random.randint(8_000, 250_000)
        self._demo_bytes[name] = (rx, tx)
        self._apply_traffic(name, rx, tx)
        self._detail_values["handshake"].setText("just now")
        self._render_state()

    def _apply_traffic(self, name: str, rx: int, tx: int) -> None:
        now = time.time()
        prev = self._samples.get(name)
        self._samples[name] = (now, rx, tx)
        self.stat_down["value"].setText(human_bytes(rx))
        self.stat_up["value"].setText(human_bytes(tx))
        if prev:
            dt = max(0.001, now - prev[0])
            rx_rate = max(0, (rx - prev[1]) / dt)
            tx_rate = max(0, (tx - prev[2]) / dt)
            self.stat_down["rate"].setText(human_rate(rx_rate))
            self.stat_up["rate"].setText(human_rate(tx_rate))
            if self.stat_down["spark"]:
                self.stat_down["spark"].push(rx_rate)
            if self.stat_up["spark"]:
                self.stat_up["spark"].push(tx_rate)

    # ------------------------------------------------------------------ settings
    def open_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(340)
        box = QVBoxLayout(dialog)
        box.setSpacing(14)
        box.addWidget(QLabel("Settings", objectName="dialogTitle"))

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme"))
        theme_row.addStretch(1)
        theme = QComboBox()
        theme.addItems(["Dark", "Light"])
        theme.setCurrentIndex(0 if self.settings.theme == "dark" else 1)
        theme_row.addWidget(theme)
        box.addLayout(theme_row)

        accent_row = QHBoxLayout()
        accent_row.addWidget(QLabel("Accent color"))
        accent_row.addStretch(1)
        accent = QComboBox()
        for label, _ in ACCENTS:
            accent.addItem(label)
        cur = next((i for i, (_, v) in enumerate(ACCENTS)
                    if v == self.settings.accent), 0)
        accent.setCurrentIndex(cur)
        accent_row.addWidget(accent)
        box.addLayout(accent_row)

        launch = QCheckBox("Connect on launch")
        launch.setChecked(self.settings.connect_on_launch)
        box.addWidget(launch)
        tray = QCheckBox("Minimize to tray on close")
        tray.setChecked(self.settings.minimize_to_tray)
        box.addWidget(tray)
        notif = QCheckBox("Show desktop notifications")
        notif.setChecked(self.settings.notifications)
        box.addWidget(notif)
        demo = QCheckBox("Demo mode (simulate connection and traffic)")
        demo.setChecked(self.settings.demo_mode)
        box.addWidget(demo)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        for b in buttons.buttons():
            if buttons.buttonRole(b) == QDialogButtonBox.AcceptRole:
                b.setObjectName("primaryBtn")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        box.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            self.settings.theme = "dark" if theme.currentIndex() == 0 else "light"
            self.settings.accent = ACCENTS[accent.currentIndex()][1]
            self.settings.connect_on_launch = launch.isChecked()
            self.settings.minimize_to_tray = tray.isChecked()
            self.settings.notifications = notif.isChecked()
            self.settings.demo_mode = demo.isChecked()
            self.settings.save()
            self._sync_power_colors()
            self._apply_theme(animate=True)
            self._render_state()
            self.statusBar().showMessage("Settings saved", 3000)

    def open_about(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"About {APP_NAME}")
        dialog.setMinimumWidth(340)
        box = QVBoxLayout(dialog)
        box.setSpacing(10)
        box.addWidget(QLabel(APP_NAME, objectName="aboutTitle"))
        box.addWidget(QLabel(f"Version {__version__}", objectName="aboutText"))
        box.addWidget(QLabel(
            "A lightweight WireGuard client.\n"
            "Imports .conf tunnels and connects through the official\n"
            "WireGuard for Windows service. Live status, traffic graphs,\n"
            "themes and system-tray control included.",
            objectName="aboutText"))
        link = QLabel(
            '<a href="https://www.wireguard.com/">wireguard.com</a>',
            objectName="aboutText")
        link.setOpenExternalLinks(True)
        box.addWidget(link)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        box.addWidget(buttons)
        dialog.exec()

    def _sync_power_colors(self) -> None:
        c = palette(self.settings.theme, self.settings.accent)
        self.power.set_colors(c["accent"], c["green"], c["muted"], c["card2"])
        if self.stat_down["spark"]:
            self.stat_down["spark"].set_color(c["green"])
        if self.stat_up["spark"]:
            self.stat_up["spark"].set_color(c["accent"])

    def _apply_theme(self, animate: bool = False) -> None:
        self.setStyleSheet(build_stylesheet(self.settings.theme, self.settings.accent))
        if animate:
            self._fade_window()

    def _fade_window(self) -> None:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.55)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _fade_in(self, widget: QWidget | None) -> None:
        if widget is None:
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.25)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    # ------------------------------------------------------------------ geometry
    def _restore_geometry(self) -> None:
        s = self.settings
        if s.win_w > 200 and s.win_h > 200:
            self.resize(s.win_w, s.win_h)
        else:
            self.resize(960, 660)
        if s.win_x >= 0 and s.win_y >= 0:
            screen = QGuiApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else None
            if avail and avail.contains(s.win_x, s.win_y):
                self.move(s.win_x, s.win_y)

    def _save_geometry(self) -> None:
        if self.isMaximized() or self.isMinimized():
            return
        self.settings.win_w = self.width()
        self.settings.win_h = self.height()
        self.settings.win_x = max(0, self.x())
        self.settings.win_y = max(0, self.y())
        self.settings.save()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _set_prop(widget: QWidget, prop: str, value: str) -> None:
        widget.setProperty(prop, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _error(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)
        self.statusBar().showMessage(message, 6000)

    def closeEvent(self, event):  # noqa: N802 (Qt naming)
        self._save_geometry()
        if getattr(self, "_force_quit", False) or not self.settings.minimize_to_tray \
                or not self.tray:
            super().closeEvent(event)
            return
        event.ignore()
        self.hide()
        self._notify(APP_NAME, "Still running in the tray. Right-click the icon to quit.",
                     any(self._connected.values()))
