"""WireGuard tunnel management backend.

On Windows this drives the official ``wireguard.exe`` that ships with
"WireGuard for Windows":

* ``wireguard.exe /installtunnelservice <conf>``   -> create + start tunnel service
* ``wireguard.exe /uninstalltunnelservice <name>`` -> stop + remove tunnel service

Live status / transfer counters are read with ``wg.exe show``.

Imported configuration files are copied into a per-user data directory so the
GUI owns a stable copy that the tunnel service can reference.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# WireGuard tunnel names are limited to this character set / length.
_VALID_NAME = re.compile(r"^[a-zA-Z0-9_=+.-]{1,15}$")

# Hide console windows spawned by subprocess on Windows.
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass
class TunnelInfo:
    """Display-friendly summary of a tunnel configuration."""

    name: str
    config_path: Path
    address: str = ""
    dns: str = ""
    endpoint: str = ""
    public_key: str = ""


@dataclass
class TunnelStatus:
    """Live status of a tunnel."""

    name: str
    connected: bool = False
    rx_bytes: int = 0
    tx_bytes: int = 0
    last_handshake: str = ""


class WireGuardError(Exception):
    """Raised when a WireGuard operation fails."""


def data_dir() -> Path:
    """Return the per-user directory that stores imported configs."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config")
        )
    path = Path(base) / "WireGuardClient" / "tunnels"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_executable(name: str) -> str | None:
    """Locate a WireGuard helper executable (wireguard.exe / wg.exe)."""
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        for candidate in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WireGuard" / name,
            Path(os.environ.get("ProgramW6432", r"C:\Program Files")) / "WireGuard" / name,
        ):
            if candidate.exists():
                return str(candidate)
    return None


def human_bytes(num: int) -> str:
    """Format a byte count as a short human readable string."""
    value = float(num)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


class WireGuardManager:
    """Manage imported WireGuard tunnels and their connection state."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or data_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)

    # -- configuration management -------------------------------------------------

    @staticmethod
    def is_valid_name(name: str) -> bool:
        return bool(_VALID_NAME.match(name))

    def list_tunnels(self) -> list[TunnelInfo]:
        tunnels = []
        for conf in sorted(self.config_dir.glob("*.conf")):
            tunnels.append(self.parse_config(conf))
        return tunnels

    def import_config(self, source: str | os.PathLike[str]) -> TunnelInfo:
        src = Path(source)
        if not src.is_file():
            raise WireGuardError(f"File not found: {src}")
        name = src.stem
        if not self.is_valid_name(name):
            raise WireGuardError(
                f"Invalid tunnel name '{name}'. Use 1-15 chars from "
                "letters, digits and _=+.-"
            )
        dest = self.config_dir / f"{name}.conf"
        shutil.copyfile(src, dest)
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
        return self.parse_config(dest)

    def delete_tunnel(self, name: str) -> None:
        conf = self.config_dir / f"{name}.conf"
        if conf.exists():
            conf.unlink()

    def parse_config(self, conf: Path) -> TunnelInfo:
        """Extract a few non-sensitive fields for display."""
        info = TunnelInfo(name=conf.stem, config_path=conf)
        section = ""
        try:
            text = conf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return info
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].lower()
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().lower()
            value = value.strip()
            if section == "interface":
                if key == "address":
                    info.address = value
                elif key == "dns":
                    info.dns = value
            elif section == "peer":
                if key == "endpoint":
                    info.endpoint = value
                elif key == "publickey":
                    info.public_key = value
        return info

    # -- connection control -------------------------------------------------------

    def _wireguard_exe(self) -> str:
        exe = _find_executable("wireguard.exe" if os.name == "nt" else "wireguard")
        if not exe:
            raise WireGuardError(
                "Could not find 'wireguard.exe'. Install WireGuard for Windows "
                "from https://www.wireguard.com/install/"
            )
        return exe

    def connect(self, name: str) -> None:
        if sys.platform != "win32":
            raise WireGuardError(
                "Connecting requires WireGuard for Windows. The GUI runs for "
                "preview, but tunnels can only be started on Windows."
            )
        conf = self.config_dir / f"{name}.conf"
        if not conf.exists():
            raise WireGuardError(f"Config not found for tunnel '{name}'.")
        self._run([self._wireguard_exe(), "/installtunnelservice", str(conf)])

    def disconnect(self, name: str) -> None:
        if sys.platform != "win32":
            raise WireGuardError("Disconnecting is only supported on Windows.")
        self._run([self._wireguard_exe(), "/uninstalltunnelservice", name])

    def status(self, name: str) -> TunnelStatus:
        status = TunnelStatus(name=name)
        wg = _find_executable("wg.exe" if os.name == "nt" else "wg")
        if not wg:
            return status
        result = self._run(
            [wg, "show", name, "dump"], check=False, capture=True
        )
        if result.returncode != 0 or not result.stdout:
            return status
        status.connected = True
        lines = result.stdout.strip().splitlines()
        # First line is the interface; peer lines follow with transfer counters.
        for line in lines[1:]:
            fields = line.split("\t")
            if len(fields) >= 7:
                try:
                    handshake = int(fields[4])
                    status.rx_bytes += int(fields[5])
                    status.tx_bytes += int(fields[6])
                    if handshake:
                        status.last_handshake = "active"
                except ValueError:
                    continue
        return status

    # -- helpers ------------------------------------------------------------------

    def _run(
        self,
        args: list[str],
        check: bool = True,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                creationflags=_NO_WINDOW,
            )
        except OSError as exc:  # pragma: no cover - depends on platform
            raise WireGuardError(f"Failed to run {args[0]}: {exc}") from exc
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise WireGuardError(detail or f"Command failed: {' '.join(args)}")
        return result
