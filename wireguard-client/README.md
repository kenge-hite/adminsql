# WireGuard Client

A minimal WireGuard client with a clean, tidy GUI. Import your existing
`.conf` files, then connect / disconnect with one click. Packs into a single
`.exe` for Windows.

![UI](docs/screenshot.png)

## Features

- Single-file Windows executable (no installer for the GUI itself).
- Minimal, evenly-spaced layout: tunnel list on the left, details + a single
  connect/disconnect button on the right.
- Import standard WireGuard `.conf` files; live status and transfer counters.

## Requirements

- **WireGuard for Windows** must be installed (the app drives its
  `wireguard.exe`): <https://www.wireguard.com/install/>
- The app requests administrator rights, which WireGuard needs to start/stop
  tunnel services.

## Run from source

```bash
pip install -r requirements.txt
python run.py
```

> On Linux/macOS the GUI runs for previewing the layout, but tunnels can only
> be started on Windows (where `wireguard.exe` is available).

## Build the single-file exe (on Windows)

```bat
build_windows.bat
```

The executable is written to `dist\WireGuardClient.exe`. Internally this runs:

```bat
pip install -r requirements.txt pyinstaller
pyinstaller wireguard-client.spec
```

## How it works

| Action      | Command                                             |
| ----------- | --------------------------------------------------- |
| Connect     | `wireguard.exe /installtunnelservice <name>.conf`   |
| Disconnect  | `wireguard.exe /uninstalltunnelservice <name>`      |
| Status      | `wg.exe show <name> dump`                           |

Imported configs are copied to `%APPDATA%\WireGuardClient\tunnels` so the GUI
keeps a stable copy that the tunnel service references.
