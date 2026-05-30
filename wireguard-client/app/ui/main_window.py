"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..wireguard import (
    TunnelInfo,
    WireGuardError,
    WireGuardManager,
    human_bytes,
)
from .styles import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, manager: WireGuardManager | None = None) -> None:
        super().__init__()
        self.manager = manager or WireGuardManager()
        self._connected: dict[str, bool] = {}

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(820, 540)
        self.setStyleSheet(STYLESHEET)

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_detail(), stretch=1)

        self.statusBar().setObjectName("statusBar")
        self.statusBar().showMessage(f"{APP_NAME} v{__version__}")

        self.refresh_tunnels()

        # Poll live status of the selected tunnel.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._poll_status)
        self._timer.start()

    # -- layout -------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(260)
        col = QVBoxLayout(sidebar)
        col.setContentsMargins(16, 18, 16, 16)
        col.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(6)
        header.addWidget(QLabel("TUNNELS", objectName="sidebarTitle"))
        header.addStretch(1)

        self.add_btn = QPushButton("+", objectName="iconButton")
        self.add_btn.setToolTip("Import a .conf file")
        self.add_btn.clicked.connect(self.import_config)
        self.remove_btn = QPushButton("\u2212", objectName="iconButton")
        self.remove_btn.setToolTip("Remove selected tunnel")
        self.remove_btn.clicked.connect(self.delete_tunnel)
        header.addWidget(self.add_btn)
        header.addWidget(self.remove_btn)
        col.addLayout(header)

        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda *_: self.update_detail())
        col.addWidget(self.list, stretch=1)

        return sidebar

    def _build_detail(self) -> QWidget:
        wrapper = QWidget()
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(28, 28, 28, 28)

        self.card = QFrame(objectName="detailCard")
        card = QVBoxLayout(self.card)
        card.setContentsMargins(28, 26, 28, 26)
        card.setSpacing(18)

        title_row = QHBoxLayout()
        self.name_label = QLabel("", objectName="tunnelName")
        self.badge = QLabel("OFFLINE", objectName="statusBadge")
        self.badge.setProperty("state", "off")
        title_row.addWidget(self.name_label)
        title_row.addStretch(1)
        title_row.addWidget(self.badge, alignment=Qt.AlignTop)
        card.addLayout(title_row)

        self.fields_box = QVBoxLayout()
        self.fields_box.setSpacing(12)
        self.address_value = self._add_field("Address")
        self.endpoint_value = self._add_field("Endpoint")
        self.dns_value = self._add_field("DNS")
        self.transfer_value = self._add_field("Transfer")
        card.addLayout(self.fields_box)

        card.addStretch(1)

        self.toggle_btn = QPushButton("Connect", objectName="primary")
        self.toggle_btn.clicked.connect(self.toggle_connection)
        card.addWidget(self.toggle_btn)

        # Empty-state hint shown when no tunnel is selected.
        self.empty_hint = QLabel(
            "No tunnel selected.\nClick  +  to import a WireGuard .conf file.",
            objectName="emptyHint",
        )
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer.addWidget(self.empty_hint, stretch=1)
        outer.addWidget(self.card, stretch=1)
        return wrapper

    def _add_field(self, label: str) -> QLabel:
        row = QVBoxLayout()
        row.setSpacing(2)
        row.addWidget(QLabel(label.upper(), objectName="fieldLabel"))
        value = QLabel("\u2014", objectName="fieldValue")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setWordWrap(True)
        row.addWidget(value)
        self.fields_box.addLayout(row)
        return value

    # -- data ---------------------------------------------------------------------

    def refresh_tunnels(self, select: str | None = None) -> None:
        current = select or self.current_name()
        self.list.blockSignals(True)
        self.list.clear()
        for tunnel in self.manager.list_tunnels():
            item = QListWidgetItem(tunnel.name)
            item.setData(Qt.UserRole, tunnel)
            self.list.addItem(item)
            if tunnel.name == current:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        self.update_detail()

    def current_tunnel(self) -> TunnelInfo | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def current_name(self) -> str | None:
        tunnel = self.current_tunnel()
        return tunnel.name if tunnel else None

    def update_detail(self) -> None:
        tunnel = self.current_tunnel()
        has = tunnel is not None
        self.card.setVisible(has)
        self.empty_hint.setVisible(not has)
        self.remove_btn.setEnabled(has)
        if not tunnel:
            return
        self.name_label.setText(tunnel.name)
        self.address_value.setText(tunnel.address or "\u2014")
        self.endpoint_value.setText(tunnel.endpoint or "\u2014")
        self.dns_value.setText(tunnel.dns or "\u2014")
        self._render_state(tunnel.name)

    def _render_state(self, name: str, rx: int = 0, tx: int = 0) -> None:
        connected = self._connected.get(name, False)
        self.badge.setText("CONNECTED" if connected else "OFFLINE")
        self.badge.setProperty("state", "on" if connected else "off")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        if connected:
            self.toggle_btn.setText("Disconnect")
            self.toggle_btn.setObjectName("danger")
            self.transfer_value.setText(
                f"\u2193 {human_bytes(rx)}    \u2191 {human_bytes(tx)}"
            )
        else:
            self.toggle_btn.setText("Connect")
            self.toggle_btn.setObjectName("primary")
            self.transfer_value.setText("\u2014")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)

    # -- actions ------------------------------------------------------------------

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
        name = self.current_name()
        if not name:
            return
        confirm = QMessageBox.question(
            self,
            "Remove tunnel",
            f"Remove tunnel '{name}'? This deletes the imported config copy.",
        )
        if confirm != QMessageBox.Yes:
            return
        if self._connected.get(name):
            try:
                self.manager.disconnect(name)
            except WireGuardError:
                pass
        self._connected.pop(name, None)
        self.manager.delete_tunnel(name)
        self.refresh_tunnels()
        self.statusBar().showMessage(f"Removed '{name}'", 4000)

    def toggle_connection(self) -> None:
        name = self.current_name()
        if not name:
            return
        try:
            if self._connected.get(name):
                self.manager.disconnect(name)
                self._connected[name] = False
                self.statusBar().showMessage(f"Disconnected '{name}'", 4000)
            else:
                self.manager.connect(name)
                self._connected[name] = True
                self.statusBar().showMessage(f"Connected '{name}'", 4000)
        except WireGuardError as exc:
            self._error(str(exc))
        self._render_state(name)

    def _poll_status(self) -> None:
        name = self.current_name()
        if not name:
            return
        try:
            status = self.manager.status(name)
        except WireGuardError:
            return
        if status.connected:
            self._connected[name] = True
        elif self._connected.get(name) and status.name == name:
            # Service reports down; reflect reality unless we never connected.
            self._connected[name] = False
        self._render_state(name, status.rx_bytes, status.tx_bytes)

    def _error(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)
        self.statusBar().showMessage(message, 6000)
