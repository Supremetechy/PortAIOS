#!/bin/bash
# MiniKernel macOS Installation Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_PREFIX="${INSTALL_PREFIX:-/usr/local/minikernel}"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           MiniKernel macOS Installation                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Error: Homebrew not found${NC}"
    echo "Please install Homebrew first: https://brew.sh"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies via Homebrew...${NC}"
brew install python@3.11 portaudio

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
sudo mkdir -p "$INSTALL_PREFIX"
sudo chown -R "$USER" "$INSTALL_PREFIX"

# Copy MiniKernel files
echo -e "${YELLOW}Installing MiniKernel...${NC}"
if [ -d "minikernel" ]; then
    cp -r minikernel "$INSTALL_PREFIX/"
    cp -r kernel/audio "$INSTALL_PREFIX/kernel/" 2>/dev/null || true
    cp -r models "$INSTALL_PREFIX/" 2>/dev/null || true
else
    echo -e "${RED}Error: Run from PortAIOS root directory${NC}"
    exit 1
fi

# Create data directories
mkdir -p "$INSTALL_PREFIX"/{data,logs,models}

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
cd "$INSTALL_PREFIX"
python3 -m pip install -r minikernel/requirements.txt

# Create launchd plist for autostart
echo -e "${YELLOW}Creating launchd service...${NC}"
cat > ~/Library/LaunchAgents/com.minikernel.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.minikernel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>$INSTALL_PREFIX/minikernel/boot.py</string>
        <string>--mode</string>
        <string>text</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_PREFIX</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$INSTALL_PREFIX/logs/minikernel.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_PREFIX/logs/minikernel.error.log</string>
</dict>
</plist>
EOF

# Create CLI wrapper
echo -e "${YELLOW}Creating CLI wrapper...${NC}"
sudo tee /usr/local/bin/minikernel > /dev/null << EOF
#!/bin/bash
cd "$INSTALL_PREFIX"
exec python3 minikernel/boot.py "\$@"
EOF
sudo chmod +x /usr/local/bin/minikernel

echo
echo -e "${GREEN}✓ Installation complete!${NC}"
echo
echo -e "${YELLOW}Quick Start:${NC}"
echo -e "  Run MiniKernel:    ${GREEN}minikernel --mode text${NC}"
echo -e "  Load at login:     ${GREEN}launchctl load ~/Library/LaunchAgents/com.minikernel.plist${NC}"
echo -e "  Start now:         ${GREEN}launchctl start com.minikernel${NC}"
echo
