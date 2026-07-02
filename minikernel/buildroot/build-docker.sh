#!/bin/bash
#
# MiniKernel Docker Build Script
# Build MiniKernel ISO using Docker (for macOS/Windows)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "=========================================="
echo "MiniKernel Docker Build"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found"
    echo ""
    echo "Please install Docker Desktop:"
    echo "  macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
    echo "  Linux: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker is not running"
    echo "Please start Docker Desktop"
    exit 1
fi

echo "✓ Docker available and running"
echo ""

# Build Docker image
echo "Building Docker build environment..."
docker build -t minikernel-builder -f "${SCRIPT_DIR}/Dockerfile.builder" "${SCRIPT_DIR}"

echo ""
echo "=========================================="
echo "Starting build in Docker container..."
echo "=========================================="
echo ""

# Run build in container
docker run --rm \
    -v "${PROJECT_ROOT}:/workspace" \
    -w /workspace/minikernel/buildroot \
    minikernel-builder \
    bash -c "
        echo 'Running build inside Docker container'
        echo 'This may take 1-2 hours on first build...'
        echo ''
        ./build.sh
    "

echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "Output files:"
ls -lh "${SCRIPT_DIR}/output/"*.iso "${SCRIPT_DIR}/output/"*.vdi 2>/dev/null || echo "No output files yet"
echo ""
