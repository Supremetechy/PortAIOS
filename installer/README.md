# PortAIOS — Desktop App Packaging

Turns PortAIOS into a double-clickable app for macOS, Windows, and Linux.
The bundled app ships with its own Python runtime, so end users don't need
Python installed.

## What end users see

- **macOS**: `PortAIOS.app` — drag into `/Applications`, double-click to launch.
- **Windows**: `PortAIOS-Setup-1.0.0.exe` installer → desktop + Start Menu shortcut.
- **Linux**: `PortAIOS-x86_64.AppImage` — `chmod +x` then double-click, or the
  unpacked `dist/PortAIOS/` folder.

First launch creates `~/Library/Application Support/PortAIOS/` (macOS),
`%APPDATA%\PortAIOS\` (Windows), or `~/.local/share/PortAIOS/` (Linux) for
config, logs, and user-downloaded models.

## Build prerequisites

You **must build on the target OS** — PyInstaller doesn't cross-compile.

- **macOS**: Xcode command-line tools, Python 3.10+
- **Windows**: Python 3.10+ from python.org, optionally
  [Inno Setup](https://jrsoftware.org/isinfo.php) for the installer EXE
- **Linux**: `python3.10+`, `python3-venv`, `curl` (for AppImage tool)

## Building

From the project root:

```bash
# macOS
bash installer/macos/build.sh
# optional: PORTAIOS_MAKE_DMG=1 bash installer/macos/build.sh
# optional: PORTAIOS_SIGN_IDENTITY="Developer ID Application: Name" bash installer/macos/build.sh

# Windows
installer\windows\build.bat
# optional: set PORTAIOS_MAKE_INSTALLER=1 && installer\windows\build.bat

# Linux
bash installer/linux/build.sh
# optional: PORTAIOS_MAKE_APPIMAGE=1 bash installer/linux/build.sh
```

Output lands in `dist/`.

## What's bundled

**Included by default:** `eel`, `bottle`, `websockets`, `numpy`, `psutil`,
`GPUtil`, `soundfile`, plus your `web/`, `assets/`, `models/`, kernel code.

**Excluded by default:** `TTS`, `torch`, `pyaudio`, `PyQt6`, `opencv-python` —
these add 1–2 GB and are optional since the UI falls back to the browser's
Web Speech API. Set `PORTAIOS_INCLUDE_TTS=1` to include them.

## Code signing

### macOS (Gatekeeper)

Unsigned apps trigger "cannot be opened because the developer cannot be
verified" on other Macs. Options:

1. **Sign + notarize** (for public distribution): set
   `PORTAIOS_SIGN_IDENTITY` to your Developer ID cert, then manually
   notarize with `xcrun notarytool` — requires a paid Apple Developer
   account ($99/year).
2. **Tell users to right-click → Open** on first launch — acceptable for
   trusted internal distribution.

### Windows (SmartScreen)

Unsigned `.exe` installers show "Windows protected your PC" warning.
Users click "More info → Run anyway." A real code-signing cert from a
CA removes this; self-signed certs don't help.

### Linux

No signing infrastructure. AppImage just works.

## Troubleshooting

- **Bundle is huge (>500 MB)**: you probably set `PORTAIOS_INCLUDE_TTS=1`.
  `torch` alone is ~800 MB. Only include if your users actually need
  server-side TTS.
- **"Module not found" at runtime**: add the module to `hiddenimports` in
  `installer/PortAIOS.spec`.
- **macOS app won't open, no error**: check
  `~/Library/Application Support/PortAIOS/portaios.log`.
- **Windows build fails on `bottle-websocket`**: install
  `Microsoft C++ Build Tools` — some deps compile from source.

## File layout

```
installer/
├── launcher.py              # PyInstaller entry point
├── first_run.py             # user data dir setup
├── PortAIOS.spec            # shared PyInstaller spec
├── requirements-build.txt   # build-time deps
├── icons/
│   ├── generate_icons.sh    # regenerates icons from one source PNG
│   ├── PortAIOS.icns        # macOS
│   ├── PortAIOS.ico         # Windows
│   └── PortAIOS.png         # Linux
├── macos/build.sh
├── windows/build.bat
├── windows/installer.iss    # Inno Setup script
└── linux/build.sh
```
