#!/usr/bin/env bash
# Build PortAIOS for Linux — produces dist/PortAIOS/ (runnable folder)
# and optionally an AppImage.
# Run from the project root:
#     bash installer/linux/build.sh
#
# Optional env vars:
#   PORTAIOS_MAKE_APPIMAGE=1  — also produce PortAIOS-x86_64.AppImage
#   PORTAIOS_INCLUDE_TTS=1    — bundle heavy TTS deps

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> PortAIOS Linux build"
echo "    Project root: $PROJECT_ROOT"

# 1. Build venv
VENV="$PROJECT_ROOT/.build-venv"
if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r installer/requirements-build.txt

# 2. Icon
if [[ ! -f installer/icons/PortAIOS.png ]]; then
    cp web/AIOSAvatarImg.png installer/icons/PortAIOS.png
fi

# 3. Clean previous build
rm -rf build dist

# 4. PyInstaller
pyinstaller installer/PortAIOS.spec --noconfirm --clean

if [[ ! -x dist/PortAIOS/PortAIOS ]]; then
    echo "Build failed — dist/PortAIOS/PortAIOS not produced" >&2
    exit 1
fi

echo "==> Built: dist/PortAIOS/"

# 5. Optional AppImage
if [[ "${PORTAIOS_MAKE_APPIMAGE:-0}" == "1" ]]; then
    echo "==> Building AppImage"

    APPDIR="dist/PortAIOS.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin"
    cp -r dist/PortAIOS/* "$APPDIR/usr/bin/"
    cp installer/icons/PortAIOS.png "$APPDIR/PortAIOS.png"

    cat > "$APPDIR/PortAIOS.desktop" <<'EOF'
[Desktop Entry]
Name=PortAIOS
Exec=PortAIOS
Icon=PortAIOS
Type=Application
Categories=Utility;
Terminal=false
EOF

    cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/bin/PortAIOS" "$@"
EOF
    chmod +x "$APPDIR/AppRun"

    # Fetch appimagetool if not on PATH
    APPIMAGETOOL="$(command -v appimagetool || echo "")"
    if [[ -z "$APPIMAGETOOL" ]]; then
        APPIMAGETOOL="./appimagetool"
        if [[ ! -x "$APPIMAGETOOL" ]]; then
            echo "    Downloading appimagetool..."
            curl -L -o appimagetool \
                https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
            chmod +x appimagetool
        fi
    fi

    "$APPIMAGETOOL" "$APPDIR" "dist/PortAIOS-x86_64.AppImage"
    echo "==> Built: dist/PortAIOS-x86_64.AppImage"
fi

echo "==> Done. Ship: dist/PortAIOS/ (or the AppImage if built)"
