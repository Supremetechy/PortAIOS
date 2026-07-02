#!/bin/bash
#
# MiniKernel Buildroot Clean Script
# Clean build artifacts and cached files
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
OUTPUT_DIR="${SCRIPT_DIR}/output"

echo "=========================================="
echo "MiniKernel Buildroot Clean"
echo "=========================================="
echo ""

echo "What would you like to clean?"
echo ""
echo "1. Clean build artifacts only (keeps downloads)"
echo "2. Clean everything including downloads"
echo "3. Clean output files only"
echo "4. Clean Buildroot config files"
echo "5. Full clean (everything)"
echo ""

read -p "Select option [1-5]: " choice

case $choice in
    1)
        echo "Cleaning build artifacts..."
        if [ -d "${BUILD_DIR}" ]; then
            cd "${BUILD_DIR}/buildroot-"* 2>/dev/null || true
            if [ -f Makefile ]; then
                make clean
            fi
            echo "✓ Build artifacts cleaned"
        else
            echo "No build directory found"
        fi
        ;;
    
    2)
        echo "Cleaning everything including downloads..."
        if [ -d "${BUILD_DIR}" ]; then
            cd "${BUILD_DIR}/buildroot-"* 2>/dev/null || true
            if [ -f Makefile ]; then
                make distclean
            fi
            echo "✓ Everything cleaned"
        else
            echo "No build directory found"
        fi
        ;;
    
    3)
        echo "Cleaning output files..."
        if [ -d "${OUTPUT_DIR}" ]; then
            rm -f "${OUTPUT_DIR}"/*.iso
            rm -f "${OUTPUT_DIR}"/*.vdi
            rm -f "${OUTPUT_DIR}"/bzImage
            rm -f "${OUTPUT_DIR}"/rootfs.*
            echo "✓ Output files cleaned"
        else
            echo "No output directory found"
        fi
        ;;
    
    4)
        echo "Cleaning Buildroot config files..."
        if [ -d "${BUILD_DIR}" ]; then
            cd "${BUILD_DIR}/buildroot-"* 2>/dev/null || true
            rm -f .config .config.old
            echo "✓ Config files cleaned"
        else
            echo "No build directory found"
        fi
        ;;
    
    5)
        echo "Full clean..."
        echo "This will remove:"
        echo "  - Build directory (${BUILD_DIR})"
        echo "  - Output directory (${OUTPUT_DIR})"
        echo ""
        read -p "Are you sure? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "${BUILD_DIR}"
            rm -rf "${OUTPUT_DIR}"
            mkdir -p "${OUTPUT_DIR}"
            touch "${OUTPUT_DIR}/.gitkeep"
            echo "✓ Full clean complete"
        else
            echo "Cancelled"
        fi
        ;;
    
    *)
        echo "Invalid selection"
        exit 1
        ;;
esac

echo ""
echo "Clean complete!"
echo ""
