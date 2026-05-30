"""Main application window: compact, minimal (Proton VPN inspired)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
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

POWER_GLYPH = "\u23fb"  # power symbol


class ClickableFrame(QFrame):
    """A QFrame that emits ``clicked`` on mouse release (used for the card)."""

    clicked = Signal()

    def mouseReleaseEvent(self, event):  # noqa: N802 (Qt naming)
        if self.isEnabled() and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, manager: WireGuardManager | None = None) -> None:
        super().__init__()
        self.manager = manager or WireGuardManager()
        self._connected: dict[str, bool] = {}
        self._tunnels: list[TunnelInfo] = []
        self._current: str | None = None

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(380, 620)
        self.setStyleSheet(STYLESHEET)

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        col = QVBoxLayout(root)
        col.setContentsMargins(22, 18, 22, 14)
        col.setSpacing(0)

        col.addLayout(self._build_header())
        col.addStretch(1)
        col.addLayout(self._build_status(), stretch=0)
        col.addStretch(1)
        col.addWidget(self._build_server_card())

        self.statusBar().setObjectName("statusBar")
        self.statusBar().showMessage(f"{APP_NAME} v{__version__}")

        self.refresh_tunnels()

        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._poll_status)
        self._timer.start()

    # -- layout -------------------------------------------------------------------

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        brand = QLabel("WIREGUARD", objectName="brand")
        dot = QLabel("\u25cf", objectName="brandDot")
        row.addWidget(dot)
        row.addSpacing(6)
        row.addWidget(brand)
        row.addStretch(1)
        return row

    def _build_status(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(16)

        self.power = QPushButton(POWER_GLYPH, objectName="powerButton")
        self.power.setCursor(Qt.PointingHandCursor)
        self.power.clicked.connect(self.toggle_connection)
        box.addWidget(self.power, alignment=Qt.AlignHCenter)

        self.status_title = QLabel("Disconnected", objectName="statusTitle")
        self.status_title.setProperty("state", "off")
        self.status_title.setAlignment(Qt.AlignHCenter)
        box.addWidget(self.status_title)

        self.status_sub = QLabel("", objectName="statusSub")
        self.status_sub.setAlignment(Qt.AlignHCenter)
        box.addWidget(self.status_sub)
        return box

    def _build_server_card(self) -> QWidget:
        self.card = ClickableFrame(objectName="serverCard")
        self.card.setCursor(Qt.PointingHandCursor)
        self.card.clicked.connect(self.open_server_menu)
        row = QHBoxLayout(self.card)
        row.setContentsMargins(14, 10, 14, 10)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(QLabel("SELECTED SERVER", objectName="cardLabel"))
        self.card_name = QLabel("\u2014", objectName="cardName")
        self.card_endpoint = QLabel("", objectName="cardEndpoint")
        texts.addWidget(self.card_name)
        texts.addWidget(self.card_endpoint)
        row.addLayout(texts, stretch=1)
        row.addWidget(QLabel("\u25be", objectName="chevron"), alignment=Qt.AlignVCenter)
        return self.card

    # -- data ---------------------------------------------------------------------

    def refresh_tunnels(self, select: str | None = None) -> None:
        self._tunnels = self.manager.list_tunnels()
        names = [t.name for t in self._tunnels]
        if select and select in names:
            self._current = select
        elif self._current not in names:
            self._current = names[0] if names else None
        self.update_detail()

    def current_tunnel(self) -> TunnelInfo | None:
        for tunnel in self._tunnels:
            if tunnel.name == self._current:
                return tunnel
        return None

    def update_detail(self) -> None:
        tunnel = self.current_tunnel()
        if tunnel is None:
            self.card_name.setText("No config")
            self.card_endpoint.setText("Click to import a .conf")
            self.power.setEnabled(False)
            self.status_title.setText("No config")
            self._set_prop(self.status_title, "state", "off")
            self.status_sub.setText("Import a WireGuard config to begin")
            return
        self.power.setEnabled(True)
        self.card_name.setText(tunnel.name)
        self.card_endpoint.setText(tunnel.endpoint or tunnel.address or "")
        self._render_state(tunnel.name)

    def _render_state(self, name: str, rx: int = 0, tx: int = 0) -> None:
        connected = self._connected.get(name, False)
        self._set_prop(self.power, "state", "on" if connected else "off")
        self._set_prop(self.status_title, "state", "on" if connected else "off")
        tunnel = self.current_tunnel()
        if connected:
            self.status_title.setText("Connected")
            self.status_sub.setText(
                f"\u2193 {human_bytes(rx)}    \u2191 {human_bytes(tx)}"
            )
        else:
            self.status_title.setText("Disconnected")
            self.status_sub.setText(
                (tunnel.endpoint or tunnel.address) if tunnel else ""
            )

    @staticmethod
    def _set_prop(widget: QWidget, prop: str, value: str) -> None:
        widget.setProperty(prop, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    # -- actions ------------------------------------------------------------------

    def open_server_menu(self) -> None:
        menu = QMenu(self)
        for tunnel in self._tunnels:
            action = QAction(tunnel.name, self, checkable=True)
            action.setChecked(tunnel.name == self._current)
            action.triggered.connect(
                lambda _=False, n=tunnel.name: self.select_tunnel(n)
            )
            menu.addAction(action)
        if self._tunnels:
            menu.addSeparator()
        import_action = QAction("Import config\u2026", self)
        import_action.triggered.connect(self.import_config)
        menu.addAction(import_action)
        if self._current:
            remove_action = QAction(f"Remove '{self._current}'", self)
            remove_action.triggered.connect(self.delete_tunnel)
            menu.addAction(remove_action)
        menu.exec(self.card.mapToGlobal(QPoint(0, self.card.height() + 4)))

    def select_tunnel(self, name: str) -> None:
        self._current = name
        self.update_detail()

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
        confirm = QMessageBox.question(
            self,
            "Remove server",
            f"Remove '{name}'? This deletes the imported config copy.",
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
        self._current = None
        self.refresh_tunnels()
        self.statusBar().showMessage(f"Removed '{name}'", 4000)

    def toggle_connection(self) -> None:
        name = self._current
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
        name = self._current
        if not name:
            return
        try:
            status = self.manager.status(name)
        except WireGuardError:
            return
        if status.connected:
            self._connected[name] = True
        elif self._connected.get(name):
            self._connected[name] = False
        self._render_state(name, status.rx_bytes, status.tx_bytes)

    def _error(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, message)
        self.statusBar().showMessage(message, 6000)
