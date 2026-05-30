"""Lightweight persisted application settings (JSON file)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
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
    connect_on_launch: bool = False
    minimize_to_tray: bool = True
    last_tunnel: str = ""

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

    def save(self) -> None:
        try:
            settings_path().write_text(
                json.dumps(asdict(self), indent=2), encoding="utf-8"
            )
        except OSError:
            pass
