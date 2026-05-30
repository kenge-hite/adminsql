---
name: testing-wireguard-client
description: Run and UI-test the compact WireGuard client GUI in wireguard-client/. Use when verifying the PySide6 app's power button, server-card menu (switch/import/remove), or connect behavior.
---

# Testing the WireGuard client GUI

The app lives in `wireguard-client/` (PySide6). Compact, Proton-style dark
window: a central circular power button + a bottom "SELECTED SERVER" card that
opens a popup menu. It manages WireGuard `.conf` files and connects via the
official Windows `wireguard.exe`.

## Run locally (Linux desktop preview)

```bash
pip install -r wireguard-client/requirements.txt   # PySide6
cd wireguard-client && DISPLAY=:0 python run.py
```

The window is fixed-size (380x620) by design — do NOT try to maximize it.
Focus it for screenshots: `DISPLAY=:0 wmctrl -a "WireGuard Client"`.

## Seeding tunnels for tests

Imported configs are copied to the per-user data dir:
- Linux: `~/.config/WireGuardClient/tunnels/<name>.conf`
- Windows: `%APPDATA%\WireGuardClient\tunnels`

Drop `.conf` files there before launch to pre-populate (tunnel name = file
stem; must match `[A-Za-z0-9_=+.-]{1,15}`). Minimal valid config:
```
[Interface]
PrivateKey = <base64>
Address = 10.0.0.2/32
DNS = 1.1.1.1
[Peer]
PublicKey = <base64>
Endpoint = host:51820
AllowedIPs = 0.0.0.0/0
```
The card + status line show the selected tunnel's Endpoint (or Address).

## UI interactions

- **Switch / import / remove:** click the bottom server card to open a popup
  menu listing all tunnels, plus `Import config…` and `Remove '<name>'`.
  Import opens a file dialog — type the full path in the File name field and
  press Enter (filtered to `*.conf`). Status bar shows `Imported '<name>'`.
- **Connect:** click the large circular power button.

## Connect behavior depends on OS

- On **Linux/macOS** the power button raises a clean error dialog: "...tunnels
  can only be started on Windows." Status stays Disconnected (purple ring) —
  this is expected, not a bug; it proves the guard + error handling work.
- The green "Connected" ring and **real connect/disconnect can only be tested
  on Windows** with WireGuard for Windows installed + a reachable WG server.
  Mark this untested when on Linux.

## Build the single-file exe

`build_windows.bat` (Windows only) → `dist\WireGuardClient.exe`. PyInstaller
does NOT cross-compile, so it cannot be built from Linux.

## Lint

```bash
cd wireguard-client && ruff check .
```

## Devin Secrets Needed

None. Testing uses dummy local `.conf` files; no credentials or VPN servers are
required for the Linux UI preview.
