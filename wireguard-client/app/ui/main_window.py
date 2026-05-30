"""Main application window: two-pane WireGuard client."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QCheckBox,
    QMenu,
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
)
from .icon import make_app_icon
from .styles import build_stylesheet

DOT = "\u25cf"


def _shorten(text: str, head: int = 10, tail: int = 6) -> str:
    if len(text) <= head + tail + 1:
        return text
    return f"{text[:head]}\u2026{text[-tail:]}"


class ServerRow(QWidget):
    """Custom row widget shown inside the sidebar server list."""

    def __init__(self, tunnel: TunnelInfo) -> None:
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

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(880, 580)
        self.resize(940, 620)
        self.setWindowIcon(make_app_icon())
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
            QTimer.singleShot(200, lambda: self._do_connect(quiet=True))

    # ------------------------------------------------------------------ sidebar
    def _build_sidebar(self) -> QWidget:
        bar = QFrame(objectName="sidebar")
        bar.setFixedWidth(252)
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

        self.list = QListWidget(objectName="serverList")
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
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

        # status card
        card = QFrame(objectName="statusCard")
        inner = QHBoxLayout(card)
        inner.setContentsMargins(22, 20, 22, 20)
        left = QVBoxLayout()
        left.setSpacing(4)
        dotrow = QHBoxLayout()
        dotrow.setSpacing(8)
        self.status_dot = QLabel(DOT, objectName="statusDot")
        self.status_dot.setProperty("state", "off")
        self.status_title = QLabel("Disconnected", objectName="statusTitle")
        self.status_title.setProperty("state", "off")
        dotrow.addWidget(self.status_dot)
        dotrow.addWidget(self.status_title)
        dotrow.addStretch(1)
        left.addLayout(dotrow)
        self.status_server = QLabel("", objectName="statusServer")
        left.addWidget(self.status_server)
        inner.addLayout(left, stretch=1)
        self.connect_btn = QPushButton("Connect", objectName="connectBtn")
        self.connect_btn.setProperty("state", "off")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.toggle_connection)
        inner.addWidget(self.connect_btn, alignment=Qt.AlignVCenter)
        col.addWidget(card)

        # stat cards
        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_duration = self._stat_card(stats, "DURATION")
        self.stat_down = self._stat_card(stats, "DOWNLOAD", accent="down")
        self.stat_up = self._stat_card(stats, "UPLOAD", accent="up")
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

    def _stat_card(self, parent: QHBoxLayout, label: str, accent: str = "") -> QLabel:
        card = QFrame(objectName="statCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 14, 18, 14)
        box.setSpacing(2)
        value = QLabel("\u2014", objectName="statValue")
        if accent:
            value.setProperty("accent", accent)
        box.addWidget(value)
        box.addWidget(QLabel(label, objectName="statLabel"))
        parent.addWidget(card, stretch=1)
        return value

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

    def _show_normal(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._force_quit = True
        QApplication.quit()

    # ------------------------------------------------------------------ data
    def refresh_tunnels(self, select: str | None = None) -> None:
        self._tunnels = self.manager.list_tunnels()
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
            widget = ServerRow(tunnel)
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
        self.update_detail()

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
        self.update_detail()

    def _filter_list(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            name = (item.data(Qt.UserRole) or "").lower()
            item.setHidden(bool(needle) and needle not in name)

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
        self._set_prop(self.status_dot, "state", "on" if connected else "off")
        self._set_prop(self.status_title, "state", "on" if connected else "off")
        self._set_prop(self.connect_btn, "state", "on" if connected else "off")
        self.status_title.setText("Connected" if connected else "Disconnected")
        self.connect_btn.setText("Disconnect" if connected else "Connect")
        self.quick.setText("Disconnect" if connected else "Quick Connect")
        label = "Disconnect" if connected else "Connect"
        if getattr(self, "tray_toggle", None):
            self.tray_toggle.setText(label)
        if self.tray:
            self.tray.setIcon(make_app_icon(connected))
        self.setWindowIcon(make_app_icon(connected))
        # update sidebar dot for current row
        for i in range(self.list.count()):
            item = self.list.item(i)
            widget = self.list.itemWidget(item)
            if isinstance(widget, ServerRow):
                widget.set_connected(self._connected.get(item.data(Qt.UserRole), False))

    def _update_stats(self) -> None:
        name = self._current
        connected = self._connected.get(name, False) if name else False
        if not connected:
            self.stat_duration.setText("\u2014")
            self.stat_down.setText("\u2014")
            self.stat_up.setText("\u2014")
            self._detail_values["handshake"].setText("\u2014")
            return
        since = self._since.get(name, time.time())
        self.stat_duration.setText(human_duration(int(time.time() - since)))

    # ------------------------------------------------------------------ actions
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
        if not name:
            return
        if self._connected.get(name):
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self, quiet: bool = False) -> None:
        name = self._current
        if not name:
            return
        try:
            self.manager.connect(name)
            self._connected[name] = True
            self._since[name] = time.time()
            self.statusBar().showMessage(f"Connected '{name}'", 4000)
            if self.tray:
                self.tray.showMessage(APP_NAME, f"Connected to {name}",
                                      make_app_icon(True), 3000)
        except WireGuardError as exc:
            if quiet:
                self.statusBar().showMessage(str(exc), 8000)
            else:
                self._error(str(exc))
        self._render_state()
        self._update_stats()

    def _do_disconnect(self) -> None:
        name = self._current
        if not name:
            return
        try:
            self.manager.disconnect(name)
        except WireGuardError as exc:
            self._error(str(exc))
        self._connected[name] = False
        self._since.pop(name, None)
        self.statusBar().showMessage(f"Disconnected '{name}'", 4000)
        self._render_state()
        self._update_stats()

    def _poll_status(self) -> None:
        name = self._current
        if not name:
            return
        try:
            status = self.manager.status(name)
        except WireGuardError:
            return
        self._connected[name] = status.connected
        if status.connected and name not in self._since:
            self._since[name] = time.time()
        if status.connected:
            self.stat_down.setText(human_bytes(status.rx_bytes))
            self.stat_up.setText(human_bytes(status.tx_bytes))
            self._detail_values["handshake"].setText(status.last_handshake or "\u2014")
        self._render_state()

    # ------------------------------------------------------------------ settings
    def open_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(320)
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

        launch = QCheckBox("Connect on launch")
        launch.setChecked(self.settings.connect_on_launch)
        box.addWidget(launch)
        tray = QCheckBox("Minimize to tray on close")
        tray.setChecked(self.settings.minimize_to_tray)
        box.addWidget(tray)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        for b in buttons.buttons():
            if buttons.buttonRole(b) == QDialogButtonBox.AcceptRole:
                b.setObjectName("primaryBtn")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        box.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            self.settings.theme = "dark" if theme.currentIndex() == 0 else "light"
            self.settings.connect_on_launch = launch.isChecked()
            self.settings.minimize_to_tray = tray.isChecked()
            self.settings.save()
            self._apply_theme()
            self.statusBar().showMessage("Settings saved", 3000)

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self.settings.theme))

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
        if getattr(self, "_force_quit", False) or not self.settings.minimize_to_tray \
                or not self.tray:
            super().closeEvent(event)
            return
        event.ignore()
        self.hide()
        self.tray.showMessage(
            APP_NAME, "Still running in the tray. Right-click the icon to quit.",
            make_app_icon(any(self._connected.values())), 3000,
        )
