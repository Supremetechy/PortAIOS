#!/usr/bin/env bash
# Generate PortAIOS.icns, PortAIOS.ico, and PortAIOS.png from a single source.
# Requires macOS (uses sips + iconutil). Run from the project root:
#     bash installer/icons/generate_icons.sh

set -euo pipefail

SRC="${1:-web/AIOSAvatarImg.png}"
OUT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -f "$SRC" ]]; then
    echo "Source image not found: $SRC" >&2
    exit 1
fi

echo "Source: $SRC"
echo "Output: $OUT_DIR"

# --- PNG (for Linux / fallback) ---
cp "$SRC" "$OUT_DIR/PortAIOS.png"
echo "Wrote PortAIOS.png"

# --- .icns (for macOS) ---
TMP_ICONSET="$(mktemp -d)/PortAIOS.iconset"
mkdir -p "$TMP_ICONSET"
for size in 16 32 64 128 256 512; do
    sips -z $size $size         "$SRC" --out "$TMP_ICONSET/icon_${size}x${size}.png"      >/dev/null
    sips -z $((size*2)) $((size*2)) "$SRC" --out "$TMP_ICONSET/icon_${size}x${size}@2x.png"  >/dev/null
done
sips -z 1024 1024 "$SRC" --out "$TMP_ICONSET/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$TMP_ICONSET" -o "$OUT_DIR/PortAIOS.icns"
rm -rf "$(dirname "$TMP_ICONSET")"
echo "Wrote PortAIOS.icns"

# --- .ico (for Windows) ---
# macOS has no native .ico writer. Use Python Pillow if available, otherwise skip.
if python3 -c "import PIL" 2>/dev/null; then
    python3 - "$SRC" "$OUT_DIR/PortAIOS.ico" <<'PY'
import sys
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
im.save(dst, format="ICO", sizes=sizes)
PY
    echo "Wrote PortAIOS.ico"
else
    echo "Skipped PortAIOS.ico — install Pillow (pip install Pillow) to generate"
fi
