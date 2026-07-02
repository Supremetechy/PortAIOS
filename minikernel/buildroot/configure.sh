#!/bin/bash
#
# MiniKernel Buildroot Configuration Script
# Select and configure build variants
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/config"

echo "=========================================="
echo "MiniKernel Buildroot Configuration"
echo "=========================================="
echo ""

# List available variants
echo "Available configurations:"
echo ""
echo "1. Standard     - Default balanced configuration (~400 MB)"
echo "2. Minimal      - Smallest possible system (~200 MB)"
echo "3. Developer    - Full development tools (~800 MB)"
echo "4. Production   - Optimized and hardened (~300 MB)"
echo "5. Custom       - Interactive configuration (menuconfig)"
echo ""

read -p "Select configuration [1-5]: " choice

case $choice in
    1)
        echo "Selected: Standard configuration"
        CONFIG_FILE="${CONFIG_DIR}/minikernel_defconfig"
        ;;
    2)
        echo "Selected: Minimal configuration"
        CONFIG_FILE="${CONFIG_DIR}/variants/minimal_defconfig"
        ;;
    3)
        echo "Selected: Developer configuration"
        CONFIG_FILE="${CONFIG_DIR}/variants/developer_defconfig"
        ;;
    4)
        echo "Selected: Production configuration"
        CONFIG_FILE="${CONFIG_DIR}/variants/production_defconfig"
        echo ""
        echo "WARNING: Production config requires setting root password hash"
        echo "Edit config/variants/production_defconfig and set:"
        echo "  BR2_TARGET_GENERIC_ROOT_PASSWD_HASH"
        echo ""
        read -p "Continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
    5)
        echo "Selected: Custom configuration"
        echo "Will run menuconfig after Buildroot setup"
        CONFIG_FILE="${CONFIG_DIR}/minikernel_defconfig"
        MENUCONFIG=1
        ;;
    *)
        echo "Invalid selection"
        exit 1
        ;;
esac

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

echo ""
echo "Configuration: $CONFIG_FILE"
echo ""

# Additional options
echo "Additional options:"
echo ""
read -p "Enable parallel build (faster)? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    PARALLEL_BUILD=1
    echo "Parallel build enabled"
else
    PARALLEL_BUILD=0
fi

echo ""
read -p "Include LLM models in ISO? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    INCLUDE_MODELS=1
    echo "Will include models (ISO will be larger)"
else
    INCLUDE_MODELS=0
fi

echo ""
read -p "Set custom ISO label? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter ISO label: " ISO_LABEL
    echo "ISO label: $ISO_LABEL"
else
    ISO_LABEL="MiniKernel"
fi

# Save configuration
cat > "${SCRIPT_DIR}/.build_config" << EOF
# MiniKernel build configuration
CONFIG_FILE=$CONFIG_FILE
PARALLEL_BUILD=$PARALLEL_BUILD
INCLUDE_MODELS=$INCLUDE_MODELS
ISO_LABEL=$ISO_LABEL
MENUCONFIG=${MENUCONFIG:-0}
EOF

echo ""
echo "=========================================="
echo "Configuration saved!"
echo "=========================================="
echo ""
echo "Configuration file: $(basename $CONFIG_FILE)"
echo "Parallel build: $([ $PARALLEL_BUILD -eq 1 ] && echo 'Yes' || echo 'No')"
echo "Include models: $([ $INCLUDE_MODELS -eq 1 ] && echo 'Yes' || echo 'No')"
echo "ISO label: $ISO_LABEL"
echo ""
echo "Run ./build.sh to start building"
echo ""
