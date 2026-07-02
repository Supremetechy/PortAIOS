#!/bin/bash
# MiniKernel Universal Deployment Script
# Automatically detects platform and deploys accordingly

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname $(dirname $(dirname $SCRIPT_DIR)))"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║           MiniKernel Universal Deployment                   ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        echo -e "${RED}Error: Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Detected OS: $OS${NC}"
}

# Show deployment options
show_menu() {
    echo
    echo -e "${YELLOW}Select deployment method:${NC}"
    echo "  1) Docker deployment (recommended)"
    echo "  2) Native installation"
    echo "  3) PyPI package installation"
    echo "  4) Development setup"
    echo "  5) Exit"
    echo
    read -p "Enter choice [1-5]: " choice
}

# Docker deployment
deploy_docker() {
    echo
    echo -e "${YELLOW}Docker Deployment${NC}"
    echo -e "${YELLOW}─────────────────${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker not found${NC}"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    echo -e "${GREEN}✓ Docker found${NC}"
    
    # Build or pull
    read -p "Build from source or pull from registry? [build/pull]: " method
    
    if [[ "$method" == "build" ]]; then
        echo "Building Docker image..."
        cd "$PROJECT_ROOT"
        docker build -f minikernel/deploy/docker/Dockerfile -t minikernel:latest .
    else
        echo "Pulling Docker image..."
        docker pull minikernel:latest
    fi
    
    echo
    echo -e "${GREEN}✓ Docker image ready${NC}"
    echo
    echo "Run with:"
    echo -e "  ${GREEN}docker run -it minikernel:latest${NC}"
    echo
    echo "Or use docker-compose:"
    echo -e "  ${GREEN}cd minikernel/deploy/docker && docker-compose up${NC}"
}

# Native installation
deploy_native() {
    echo
    echo -e "${YELLOW}Native Installation${NC}"
    echo -e "${YELLOW}──────────────────${NC}"
    
    case "$OS" in
        linux)
            if [ "$EUID" -ne 0 ]; then
                echo -e "${RED}Error: Please run as root (use sudo)${NC}"
                return 1
            fi
            bash "$SCRIPT_DIR/../installers/install-linux.sh"
            ;;
        macos)
            bash "$SCRIPT_DIR/../installers/install-macos.sh"
            ;;
        windows)
            echo "Please run install-windows.ps1 in PowerShell as Administrator"
            ;;
    esac
}

# PyPI installation
deploy_pypi() {
    echo
    echo -e "${YELLOW}PyPI Package Installation${NC}"
    echo -e "${YELLOW}─────────────────────────${NC}"
    
    # Check pip
    if ! command -v pip &> /dev/null; then
        echo -e "${RED}Error: pip not found${NC}"
        return 1
    fi
    
    echo "Installing MiniKernel from source..."
    cd "$PROJECT_ROOT/minikernel"
    pip install -e .
    
    echo
    echo -e "${GREEN}✓ MiniKernel installed${NC}"
    echo
    echo "Run with:"
    echo -e "  ${GREEN}minikernel --mode text${NC}"
}

# Development setup
deploy_dev() {
    echo
    echo -e "${YELLOW}Development Setup${NC}"
    echo -e "${YELLOW}────────────────${NC}"
    
    cd "$PROJECT_ROOT/minikernel"
    
    # Create virtual environment
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e ".[dev]"
    
    echo
    echo -e "${GREEN}✓ Development environment ready${NC}"
    echo
    echo "Activate with:"
    echo -e "  ${GREEN}source venv/bin/activate${NC}"
    echo
    echo "Run tests with:"
    echo -e "  ${GREEN}pytest tests/${NC}"
    echo
    echo "Run MiniKernel:"
    echo -e "  ${GREEN}python boot.py --mode text${NC}"
}

# Main menu loop
main() {
    detect_os
    
    while true; do
        show_menu
        
        case $choice in
            1)
                deploy_docker
                break
                ;;
            2)
                deploy_native
                break
                ;;
            3)
                deploy_pypi
                break
                ;;
            4)
                deploy_dev
                break
                ;;
            5)
                echo "Exiting..."
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                ;;
        esac
    done
    
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         ✓ Deployment Complete!                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Run main
main "$@"
