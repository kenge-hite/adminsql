"""Lightweight persisted application settings (JSON file)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _config_root() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    path = Path(base) / "WireGuardClient"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return _config_root() / "settings.json"


@dataclass
class Settings:
    """User preferences persisted between runs."""

    theme: str = "dark"            # "dark" | "light"
    accent: str = "#7d4dff"        # accent / brand color
    connect_on_launch: bool = False
    minimize_to_tray: bool = True
    notifications: bool = True     # system tray notifications
    demo_mode: bool = False        # simulate a connection (preview animations)
    last_tunnel: str = ""
    pinned: list = field(default_factory=list)   # pinned tunnel names
    recent: list = field(default_factory=list)   # recently used tunnel names
    win_w: int = 0
    win_h: int = 0
    win_x: int = -1
    win_y: int = -1

    @classmethod
    def load(cls) -> Settings:
        path = settings_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in valid})

    def mark_recent(self, name: str, limit: int = 5) -> None:
        if not name:
            return
        if name in self.recent:
            self.recent.remove(name)
        self.recent.insert(0, name)
        del self.recent[limit:]

    def toggle_pin(self, name: str) -> bool:
        if name in self.pinned:
            self.pinned.remove(name)
            return False
        self.pinned.append(name)
        return True

    def save(self) -> None:
        try:
            settings_path().write_text(
                json.dumps(asdict(self), indent=2), encoding="utf-8"
            )
        except OSError:
            pass
