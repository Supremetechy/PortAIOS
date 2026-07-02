#!/bin/bash
#
# MiniKernel Buildroot Build Script
# Builds a bootable ISO image for VirtualBox
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MINIKERNEL_ROOT="$(dirname "$SCRIPT_DIR")"
BUILDROOT_VERSION="2024.02"
BUILDROOT_URL="https://buildroot.org/downloads/buildroot-${BUILDROOT_VERSION}.tar.gz"
BUILD_DIR="${SCRIPT_DIR}/build"
OUTPUT_DIR="${SCRIPT_DIR}/output"

echo "=========================================="
echo "MiniKernel Buildroot Build System"
echo "=========================================="

# Check dependencies
check_dependencies() {
    echo "Checking build dependencies..."
    
    local deps="gcc g++ make patch perl python3 rsync wget tar gzip bzip2 which"
    local missing=""
    
    for dep in $deps; do
        if ! command -v $dep &> /dev/null; then
            missing="$missing $dep"
        fi
    done
    
    if [ -n "$missing" ]; then
        echo "ERROR: Missing dependencies:$missing"
        echo "On Ubuntu/Debian: sudo apt-get install build-essential libncurses-dev rsync"
        exit 1
    fi
    
    echo "✓ All dependencies found"
}

# Download Buildroot
download_buildroot() {
    if [ -d "${BUILD_DIR}/buildroot-${BUILDROOT_VERSION}" ]; then
        echo "Buildroot already downloaded"
        return
    fi
    
    echo "Downloading Buildroot ${BUILDROOT_VERSION}..."
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    
    wget -c "${BUILDROOT_URL}"
    tar xzf "buildroot-${BUILDROOT_VERSION}.tar.gz"
    
    echo "✓ Buildroot downloaded"
}

# Configure Buildroot
configure_buildroot() {
    echo "Configuring Buildroot for MiniKernel..."
    cd "${BUILD_DIR}/buildroot-${BUILDROOT_VERSION}"
    
    # Clean any existing config AND run distclean
    echo "Cleaning old configurations..."
    make distclean 2>/dev/null || true
    rm -f .config .config.old .config.bak
    
    # Use our defconfig
    make defconfig BR2_DEFCONFIG="${SCRIPT_DIR}/config/minikernel_defconfig"
    
    # Set overlay directory using sed instead of append
    sed -i.bak '/BR2_ROOTFS_OVERLAY/d' .config
    echo "BR2_ROOTFS_OVERLAY=\"${SCRIPT_DIR}/overlay\"" >> .config
    
    echo "✓ Buildroot configured"
}

# Copy MiniKernel into overlay
prepare_minikernel() {
    echo "Preparing MiniKernel for inclusion in rootfs..."
    
    local overlay_minikernel="${SCRIPT_DIR}/overlay/opt/minikernel"
    mkdir -p "$overlay_minikernel"
    
    # Copy MiniKernel source
    rsync -av --exclude='buildroot' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              --exclude='.git' \
              "${MINIKERNEL_ROOT}/" \
              "$overlay_minikernel/"
    
    # Copy models if they exist
    if [ -d "${MINIKERNEL_ROOT}/../models" ]; then
        mkdir -p "${overlay_minikernel}/models"
        cp -r "${MINIKERNEL_ROOT}/../models/"* "${overlay_minikernel}/models/" || true
    fi
    
    # Create requirements.txt for Python packages
    cat > "${overlay_minikernel}/requirements.txt" << 'EOF'
# MiniKernel Python dependencies (minimal for embedded)
# Most packages are built into Buildroot

# Core dependencies built by Buildroot:
# - numpy
# - sqlite3

# Additional packages to install at runtime
EOF
    
    echo "✓ MiniKernel prepared"
}

# Build the system
build_system() {
    echo "Building system (this will take a while)..."
    cd "${BUILD_DIR}/buildroot-${BUILDROOT_VERSION}"
    
    # Build with all CPU cores
    make -j$(nproc)
    
    echo "✓ Build completed"
}

# Create output artifacts
create_artifacts() {
    echo "Creating output artifacts..."
    
    mkdir -p "${OUTPUT_DIR}"
    
    local images_dir="${BUILD_DIR}/buildroot-${BUILDROOT_VERSION}/output/images"
    
    # Copy ISO
    if [ -f "${images_dir}/rootfs.iso9660" ]; then
        cp "${images_dir}/rootfs.iso9660" "${OUTPUT_DIR}/minikernel.iso"
        echo "✓ Bootable ISO: ${OUTPUT_DIR}/minikernel.iso"
    fi
    
    # Copy kernel
    if [ -f "${images_dir}/bzImage" ]; then
        cp "${images_dir}/bzImage" "${OUTPUT_DIR}/bzImage"
        echo "✓ Kernel: ${OUTPUT_DIR}/bzImage"
    fi
    
    # Copy rootfs
    if [ -f "${images_dir}/rootfs.ext2" ]; then
        cp "${images_dir}/rootfs.ext2" "${OUTPUT_DIR}/rootfs.ext2"
        echo "✓ Root filesystem: ${OUTPUT_DIR}/rootfs.ext2"
    fi
    
    # Create VirtualBox disk
    create_vbox_disk
}

# Create VirtualBox persistent disk
create_vbox_disk() {
    echo "Creating VirtualBox persistent disk..."
    
    if command -v VBoxManage &> /dev/null; then
        local vdi_path="${OUTPUT_DIR}/minikernel-persistent.vdi"
        
        # Create 8GB dynamic disk
        VBoxManage createmedium disk \
            --filename "$vdi_path" \
            --size 8192 \
            --format VDI \
            --variant Standard
        
        echo "✓ VirtualBox disk: $vdi_path"
    else
        echo "⚠ VBoxManage not found, skipping VDI creation"
        echo "  Install VirtualBox to create persistent disks"
    fi
}

# Print usage instructions
print_usage() {
    cat << EOF

========================================
Build Complete!
========================================

Output files in: ${OUTPUT_DIR}/

To test in VirtualBox:
  1. Create a new VM:
     - Type: Linux
     - Version: Other Linux (64-bit)
     - Memory: 2048 MB
     - Disk: Use ${OUTPUT_DIR}/minikernel-persistent.vdi
  
  2. Configure VM:
     - Storage: Add IDE CD/DVD with minikernel.iso
     - Network: Enable NAT
     - Audio: Enable audio output
  
  3. Boot and enjoy MiniKernel!

Manual build steps:
  ./build.sh clean          - Clean build artifacts
  ./build.sh menuconfig     - Configure Buildroot interactively
  ./build.sh rebuild        - Rebuild without cleaning

EOF
}

# Main build flow
main() {
    case "${1:-build}" in
        clean)
            echo "Cleaning build artifacts..."
            rm -rf "${BUILD_DIR}"
            rm -rf "${OUTPUT_DIR}"
            echo "✓ Cleaned"
            ;;
        
        menuconfig)
            cd "${BUILD_DIR}/buildroot-${BUILDROOT_VERSION}"
            make menuconfig
            ;;
        
        rebuild)
            build_system
            create_artifacts
            print_usage
            ;;
        
        build|*)
            check_dependencies
            download_buildroot
            configure_buildroot
            prepare_minikernel
            build_system
            create_artifacts
            print_usage
            ;;
    esac
}

main "$@"
