# WireGuard Client

A clean WireGuard client GUI. Import your existing `.conf` files and connect /
disconnect with one click. Packs into a single `.exe` for Windows.

![UI](docs/screenshot.png)

## Features

- Two-pane layout: searchable server list on the left, live connection
  dashboard on the right.
- **Animated power button** with press feedback, a connecting spinner and a
  pulsing glow ring when connected; a breathing status dot.
- **Live traffic graphs**: sparkline charts plus real-time download / upload
  rates (B/s → GB/s) computed from transfer deltas.
- **Quick Connect** and one-click connect / disconnect with a connecting
  animation and desktop notifications.
- Connection stats: live duration timer, download / upload totals.
- Full tunnel details: address, DNS, endpoint, allowed IPs, public key,
  latest handshake. One-click **copy** of the public key / endpoint.
- **Pin** favorite servers to the top and jump back to **recent** servers
  via chips.
- **View config** (raw `.conf` with the private key masked).
- **Settings**: dark / light theme + **accent color** (persisted), animated
  theme transition, connect-on-launch, minimize-to-tray, notifications, and a
  **demo mode** that simulates a connection so you can preview the animated UI
  on any OS.
- Remembers window size & position. **About** dialog.
- System tray icon (connect / disconnect / show / quit).
- Single-file Windows executable (no installer for the GUI itself).

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
keeps a stable copy that the tunnel service references. Preferences are stored
in `%APPDATA%\WireGuardClient\settings.json` (`~/.config/WireGuardClient` on
Linux/macOS).
