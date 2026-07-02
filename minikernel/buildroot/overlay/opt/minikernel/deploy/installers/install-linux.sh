#!/bin/bash
# MiniKernel Linux Installation Script
# Supports Ubuntu/Debian, Fedora/RHEL, Arch Linux

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation prefix
INSTALL_PREFIX="${INSTALL_PREFIX:-/opt/minikernel}"
INSTALL_USER="${INSTALL_USER:-minikernel}"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║           MiniKernel Installation Script                    ║${NC}"
echo -e "${GREEN}║    AI-First Voice-Controlled Operating System               ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (use sudo)${NC}"
    exit 1
fi

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        echo -e "${RED}Error: Cannot detect OS${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Detected OS: $OS $OS_VERSION${NC}"
}

# Install system dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing system dependencies...${NC}"
    
    case "$OS" in
        ubuntu|debian)
            apt-get update
            apt-get install -y \
                python3 \
                python3-pip \
                python3-venv \
                portaudio19-dev \
                alsa-utils \
                build-essential \
                git
            ;;
        fedora|rhel|centos)
            dnf install -y \
                python3 \
                python3-pip \
                portaudio-devel \
                alsa-utils \
                gcc \
                git
            ;;
        arch)
            pacman -Sy --noconfirm \
                python \
                python-pip \
                portaudio \
                alsa-utils \
                base-devel \
                git
            ;;
        *)
            echo -e "${RED}Error: Unsupported OS: $OS${NC}"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}✓ System dependencies installed${NC}"
}

# Create minikernel user
create_user() {
    if id "$INSTALL_USER" &>/dev/null; then
        echo -e "${YELLOW}User $INSTALL_USER already exists${NC}"
    else
        echo -e "${YELLOW}Creating user $INSTALL_USER...${NC}"
        useradd -r -m -s /bin/bash -d "$INSTALL_PREFIX" "$INSTALL_USER"
        usermod -aG audio "$INSTALL_USER"
        echo -e "${GREEN}✓ User created${NC}"
    fi
}

# Install MiniKernel
install_minikernel() {
    echo -e "${YELLOW}Installing MiniKernel...${NC}"
    
    # Create installation directory
    mkdir -p "$INSTALL_PREFIX"
    
    # Copy files (assumes running from repo root)
    if [ -d "minikernel" ]; then
        cp -r minikernel "$INSTALL_PREFIX/"
        cp -r kernel/audio "$INSTALL_PREFIX/kernel/" 2>/dev/null || true
        cp -r models "$INSTALL_PREFIX/" 2>/dev/null || true
    else
        echo -e "${RED}Error: minikernel directory not found${NC}"
        echo "Please run this script from the PortAIOS root directory"
        exit 1
    fi
    
    # Create data directories
    mkdir -p "$INSTALL_PREFIX"/{data,logs,models}
    
    # Set ownership
    chown -R "$INSTALL_USER:$INSTALL_USER" "$INSTALL_PREFIX"
    
    echo -e "${GREEN}✓ MiniKernel installed to $INSTALL_PREFIX${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    
    # Install as minikernel user
    sudo -u "$INSTALL_USER" bash << EOF
cd "$INSTALL_PREFIX"
python3 -m pip install --user --upgrade pip
python3 -m pip install --user -r minikernel/requirements.txt
EOF
    
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
}

# Install systemd service
install_systemd_service() {
    echo -e "${YELLOW}Installing systemd service...${NC}"
    
    # Copy service files
    if [ -f "minikernel/deploy/systemd/minikernel.service" ]; then
        cp minikernel/deploy/systemd/minikernel.service /etc/systemd/system/
        cp minikernel/deploy/systemd/minikernel-voice.service /etc/systemd/system/
        
        # Update paths in service files
        sed -i "s|/opt/minikernel|$INSTALL_PREFIX|g" /etc/systemd/system/minikernel.service
        sed -i "s|/opt/minikernel|$INSTALL_PREFIX|g" /etc/systemd/system/minikernel-voice.service
        
        # Reload systemd
        systemctl daemon-reload
        
        echo -e "${GREEN}✓ Systemd service installed${NC}"
        echo -e "${YELLOW}  To enable: sudo systemctl enable minikernel${NC}"
        echo -e "${YELLOW}  To start:  sudo systemctl start minikernel${NC}"
    else
        echo -e "${YELLOW}⚠ Systemd service files not found, skipping${NC}"
    fi
}

# Create CLI wrapper
create_cli_wrapper() {
    echo -e "${YELLOW}Creating CLI wrapper...${NC}"
    
    cat > /usr/local/bin/minikernel << EOF
#!/bin/bash
# MiniKernel CLI wrapper
cd "$INSTALL_PREFIX"
exec python3 minikernel/boot.py "\$@"
EOF
    
    chmod +x /usr/local/bin/minikernel
    
    echo -e "${GREEN}✓ CLI wrapper created at /usr/local/bin/minikernel${NC}"
}

# Main installation
main() {
    detect_os
    install_dependencies
    create_user
    install_minikernel
    install_python_deps
    install_systemd_service
    create_cli_wrapper
    
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║         ✓ MiniKernel Installation Complete!                 ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${YELLOW}Quick Start:${NC}"
    echo -e "  1. Start MiniKernel:     ${GREEN}minikernel --mode text${NC}"
    echo -e "  2. Enable service:       ${GREEN}sudo systemctl enable minikernel${NC}"
    echo -e "  3. Start service:        ${GREEN}sudo systemctl start minikernel${NC}"
    echo -e "  4. Check status:         ${GREEN}sudo systemctl status minikernel${NC}"
    echo
    echo -e "${YELLOW}Installation location:${NC} $INSTALL_PREFIX"
    echo -e "${YELLOW}User:${NC} $INSTALL_USER"
    echo
}

# Run installation
main "$@"
