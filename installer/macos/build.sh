#!/usr/bin/env bash
# Build PortAIOS.app (and optionally a .dmg) on macOS.
# Run from the project root:
#     bash installer/macos/build.sh
#
# Optional env vars:
#   PORTAIOS_SIGN_IDENTITY="Developer ID Application: …"  — enables code signing
#   PORTAIOS_MAKE_DMG=1                                   — also produce .dmg
#   PORTAIOS_INCLUDE_TTS=1                                — bundle heavy TTS deps

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> PortAIOS macOS build"
echo "    Project root: $PROJECT_ROOT"

# 1. Fresh build venv so stale deps don't bleed into the bundle
VENV="$PROJECT_ROOT/.build-venv"
if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r installer/requirements-build.txt

# 2. Generate icons if missing
if [[ ! -f installer/icons/PortAIOS.icns ]]; then
    bash installer/icons/generate_icons.sh web/AIOSAvatarImg.png
fi

# 3. Clean previous build
rm -rf build dist

# 4. Run PyInstaller
pyinstaller installer/PortAIOS.spec --noconfirm --clean

APP="dist/PortAIOS.app"
if [[ ! -d "$APP" ]]; then
    echo "Build failed — $APP not produced" >&2
    exit 1
fi

echo "==> Built: $APP"

# 5. Code signing
#    Entitlements (mic, camera, hardened-runtime shims) must be applied
#    even for ad-hoc local builds — otherwise macOS TCC silently denies
#    microphone access when Chrome is launched from the bundle.
ENTITLEMENTS="$PROJECT_ROOT/installer/macos/entitlements.plist"

if [[ -n "${PORTAIOS_SIGN_IDENTITY:-}" ]]; then
    echo "==> Code signing with: $PORTAIOS_SIGN_IDENTITY"
    SIGN_ID="$PORTAIOS_SIGN_IDENTITY"
else
    echo "==> Ad-hoc signing with entitlements (no Developer ID set)"
    echo "    Unsigned distribution still triggers Gatekeeper on other Macs."
    SIGN_ID="-"
fi

codesign --deep --force --verify --verbose \
    --sign "$SIGN_ID" \
    --options runtime \
    --entitlements "$ENTITLEMENTS" \
    "$APP"

codesign --verify --verbose "$APP"
# Show what got embedded so voice/mic regressions are easy to diagnose.
codesign -d --entitlements :- "$APP" 2>&1 | head -40 || true

# 6. Optional DMG
if [[ "${PORTAIOS_MAKE_DMG:-0}" == "1" ]]; then
    echo "==> Building DMG"
    DMG="dist/PortAIOS.dmg"
    rm -f "$DMG"
    hdiutil create -volname "PortAIOS" -srcfolder "$APP" -ov -format UDZO "$DMG"
    echo "==> Built: $DMG"
fi

echo "==> Done. Ship: $APP"
